# MODEL_SERVICE/icu_congestion/api/main.py
import os
import pickle
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# ─────────────────────────────────────────────────
# 1) .env 로드
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

MODEL_RELOAD_INTERVAL = int(os.getenv("MODEL_RELOAD_INTERVAL", "10"))
CONG_MODEL_PATH       = ROOT / "icu_congestion" / "model" / "catboost_model.pkl"

icu_cong_model = None
cong_mtime     = 0.0

# ─────────────────────────────────────────────────
# 2) DB 컬럼명 -> 학습 피처명 매핑 (단일 컬럼만)
from icu_congestion.utils.column_mapping import COLUMN_MAPPING

# ─────────────────────────────────────────────────
# 3) Pydantic 스키마 import
from api.schemas import PredictRequest

# ─────────────────────────────────────────────────
# 4) 전처리 함수 import
from icu_congestion.retrain.utils import preprocess as preprocess_cong

# ─────────────────────────────────────────────────
# 5) 모델 핫리로드 헬퍼
def _hot_reload():
    global icu_cong_model, cong_mtime
    try:
        mtime = CONG_MODEL_PATH.stat().st_mtime
        if mtime != cong_mtime:
            with open(CONG_MODEL_PATH, "rb") as f:
                icu_cong_model = pickle.load(f)
            cong_mtime = mtime
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Model not found: {e}")

# ─────────────────────────────────────────────────
# 6) Lifespan 이벤트로 서버 시작 시 1회 로드
@asynccontextmanager
async def lifespan(app: FastAPI):
    _hot_reload()
    yield

app = FastAPI(
    title="ICU Congestion API",
    version="1.0.0",
    lifespan=lifespan
)

# ─────────────────────────────────────────────────
# 7) 헬스체크
@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat()
    }

# ─────────────────────────────────────────────────
# 8) 예측 엔드포인트
@app.post("/icu/congestion/predict", tags=["prediction"])
def predict_congestion(req: PredictRequest):
    _hot_reload()

    # 8-1) trasNo -> datetime 
    try:
        record_time = datetime.strptime(req.trasNo, "%Y%m%d%H%M%S") \
                             .replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="trasNo 포맷 오류 (YYYYMMDDHHMMSS)")

    # 8-2) 중첩 JSON 풀어서 DataFrame
    rows = []
    for info in req.ptrmInfo:
        for dtl in info.ptntDtlsCtrlAllLst:
            for ward in dtl.wardLst:
                rows.append({
                    "wardCd":       ward.wardCd,
                    "embdCct":      ward.embdCct,
                    "dschCct":      ward.dschCct,
                    "useSckbCnt":   ward.useSckbCnt,
                    "admsApntCct":  ward.admsApntCct,
                    "chupCct":      ward.chupCct,
                    "record_time":  record_time,
                })
    if not rows:
        raise HTTPException(status_code=400, detail="병상 정보가 없습니다")

    df = pd.DataFrame(rows)

    # 8-3) total_beds 계산 & 원본문 삭제
    df["total_beds"] = df[[
        "embdCct","dschCct","useSckbCnt","admsApntCct","chupCct"
    ]].sum(axis=1)
    df.drop(columns=[
        "embdCct","dschCct","useSckbCnt","admsApntCct","chupCct"
    ], inplace=True)

    # 8-4) 컬럼명 매핑 (단일 컬럼만)
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    # 8-5) 학습에 사용하지 않을 컬럼 삭제
    df.drop(columns=["ratio_male_female","ratio_elder"], 
            errors="ignore", inplace=True)

    # 8-6) 파생 피처 생성
    df["free_beds"]        = df["total_beds"] - df["occupied_beds"]
    df["occ_rate"]         = df["occupied_beds"] / df["total_beds"]
    df["occupancy_change"] = (
        df["occupied_beds"]
      - df["discharges_24h"]
      + df["admissions_24h"]
    )

    # 8-7) 전처리 -> 예측
    X     = preprocess_cong(df)
    preds = icu_cong_model.predict(X).astype(int).tolist()

    # 8-8) 응답
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "request_time": record_time.isoformat(),
        "results": [
            {"date": today, "congestion_flag": p}
            for p in preds
        ]
    }

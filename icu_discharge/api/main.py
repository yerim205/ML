import os
import pickle
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# 1) .env 로드
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

MODEL_RELOAD_INTERVAL = int(os.getenv("MODEL_RELOAD_INTERVAL", "10"))
DIS_MODEL_PATH = ROOT / "icu_discharge" / "model" / "best_catboost_model.pkl"

icu_dis_model = None
dis_mtime = 0.0

# 2) DB 컬럼명 → 학습 피처명 매핑
from icu_discharge.utils.column_mapping import COLUMN_MAPPING

# 3) Pydantic 스키마 import
from api.schemas import PredictRequest

# 4) 전처리 함수 import
from icu_discharge.retrain.utils import preprocess as preprocess_dis

# 5) 모델 핫리로드 헬퍼
def _hot_reload():
    global icu_dis_model, dis_mtime
    try:
        mtime = DIS_MODEL_PATH.stat().st_mtime
        if mtime != dis_mtime:
            with open(DIS_MODEL_PATH, "rb") as f:
                icu_dis_model = pickle.load(f)
            dis_mtime = mtime
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Model not found: {e}")

# 6) Lifespan 이벤트로 서버 시작 시 1회 로드
@asynccontextmanager
async def lifespan(app: FastAPI):
    _hot_reload()
    yield

app = FastAPI(
    title="ICU Discharge API",
    version="1.0.0",
    lifespan=lifespan
)

# 7) 헬스체크
@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat()
    }

# 8) 예측 엔드포인트
@app.post("/icu/discharge/predict", tags=["prediction"])
def predict_discharge(req: PredictRequest):
    _hot_reload()

    # trasNo → datetime (UTC)
    try:
        record_time = datetime.strptime(req.trasNo, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="trasNo 포맷 오류 (YYYYMMDDHHMMSS)")

    # 중첩 JSON 풀어서 DataFrame
    rows = []
    for info in req.ptrmInfo:
        for dtl in info.ptntDtlsCtrlAllLst:
            for ward in dtl.wardLst:
                rows.append({
                    "wardCd": ward.wardCd,
                    "embdCct": ward.embdCct,
                    "dschCct": ward.dschCct,
                    "useSckbCnt": ward.useSckbCnt,
                    "admsApntCct": ward.admsApntCct,
                    "chupCct": ward.chupCct,
                    "record_time": record_time,
                })
    if not rows:
        raise HTTPException(status_code=400, detail="병상 정보가 없습니다")

    df = pd.DataFrame(rows)

    # total_beds 계산 & 원본문 삭제
    df["total_beds"] = df[[
        "embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"
    ]].sum(axis=1)
    df.drop(columns=[
        "embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"
    ], inplace=True)

    # 컬럼명 매핑
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    # 학습에 사용하지 않을 컬럼 삭제
    df.drop(columns=["ratio_male_female","ratio_elder"], errors="ignore", inplace=True)

    # 파생 피처 생성 (discharge 모델에 맞게 수정 필요)
    # 예시: df["discharge_rate"] = ...
    # 아래는 임시 예시
    df["free_beds"] = df["total_beds"] - df["occupied_beds"]
    df["discharge_rate"] = df["discharges_24h"] / df["total_beds"]

    # 전처리 → 예측
    X = preprocess_dis(df)
    preds = icu_dis_model.predict(X).tolist()  # 회귀면 float, 분류면 int

    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "request_time": record_time.isoformat(),
        "results": [
            {"date": today, "discharge_pred": p}
            for p in preds
        ]
    }

# retrain/icu_congestion_retrain.py
import os
import sys
import json
import joblib
import shutil
import logging
import pandas as pd

from pathlib import Path
from datetime import datetime, timezone
from catboost import CatBoostClassifier
from dotenv import load_dotenv

# ─── 경로 및 환경설정 ─────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(dotenv_path=ROOT / ".env")

# 추가 드론 기능 가져오기
from utils.db_loader import get_api_logs_raw
from utils.preprocess import parse_model23_input, preprocess
from utils.ncp_client import upload_file_to_ncp

MODEL_SAVE_PATH = ROOT / "model" / "model2.pkl"
ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
NCP_MODEL_KEY = "rmrp-models/model2.pkl"

# 포맷 설정
MODEL_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
ARCHIVE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("ICU_RETRAIN")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ─── 병상 데이터 로딩 및 파싱 ─────────────────────────
def load_parsed_records(days: int = 1) -> pd.DataFrame:
    raw_df = get_api_logs_raw(days)
    if raw_df.empty:
        logger.warning("[ICU] 병상 API 로그가 비어 있습니다.")
        return pd.DataFrame()

    records = []
    for ct, reg_dtm in zip(raw_df["ctnt"], raw_df["reg_dtm"]):
        try:
            j = json.loads(ct)
            j["_timestamp"] = reg_dtm.replace(tzinfo=timezone.utc)
            records.extend(parse_model23_input(j))
        except Exception as e:
            logger.warning(f"[ICU] JSON 파싱 실패 → {e}")
            continue

    return pd.DataFrame(records)


# ─── 모델 저장 및 NCP 업로드 ─────────────────────────
def save_model_and_upload(model_dict: dict):
    # 1. 로컬 저장
    joblib.dump(model_dict, MODEL_SAVE_PATH)

    # 2. 버전 아카이브 저장
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_path = ARCHIVE_MODEL_DIR / f"icu_congestion_{ts}.pkl"
    shutil.copy(MODEL_SAVE_PATH, archive_path)
    logger.info(f"[저장] 로컬 모델 → {MODEL_SAVE_PATH}")
    logger.info(f"[저장] 아카이브 → {archive_path}")

    # 3. NCP 업로드
    try:
        upload_file_to_ncp(str(MODEL_SAVE_PATH), NCP_MODEL_KEY)
        logger.info(f"[NCP] 업로드 완료 → {NCP_MODEL_KEY}")
    except Exception as e:
        logger.error(f"[NCP] 업로드 실패 → {e}")



# ─── 메인 재학습 함수 ───────────────────────
def model2_retrain():
    logger.info("ICU 혼잡도 모델 재학습 시작")

    raw_df = get_api_logs_raw(days=1)
    if raw_df.empty:
        logger.warning(" 병상 API 로그 데이터가 없습니다.")
        return

    records = []
    for ct, reg_dtm in zip(raw_df["ctnt"], raw_df["reg_dtm"]):
        try:
            j = json.loads(ct)
            j["_timestamp"] = reg_dtm.replace(tzinfo=timezone.utc)
            records.extend(parse_model23_input(j))
        except Exception as e:
            logger.warning(f"JSON 파싱 실패: {e}")
            continue

    df = pd.DataFrame(records)
    if df.empty:
        logger.warning("파싱된 병상 데이터가 없습니다.")
        return

    # ── 1. 7일 평균 혼잡도 생성 ─────────────────
    hist7 = (
        df.assign(total=lambda x: x.embdCct + x.dschCct + x.useSckbCnt + x.admsApntCct + x.chupCct)
          .eval("occ_rate = embdCct / total")
          .groupby("wardCd")["occ_rate"]
          .mean()
          .rename("occ_rate_7d_ago")
          .reset_index()
    )
    df = df.merge(hist7, on="wardCd", how="left")

    # ── 2. 피처 및 타깃 생성 ───────────────────
    df["total_beds"] = df[["embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"]].sum(axis=1)
    df["occupied_beds"] = df["useSckbCnt"]

    df["congestion_flag"] = (df.occupied_beds / df.total_beds > 0.9).astype(int)
    y = df.pop("congestion_flag")

    # ── 3. 전처리 ───────────────────────────────
    X = preprocess(df)
    cat_idx = [X.columns.get_loc("ward_code")]

    # ── 4. 모델 학습 ────────────────────────────
    model = CatBoostClassifier(
        depth=6,
        iterations=400,
        learning_rate=0.07,
        cat_features=cat_idx,
        loss_function="Logloss",
        random_state=42,
        verbose=False
    )
    model.fit(X, y)

    # ── 모델 저장 및 업로드 ─────────────────────────────
    save_model_and_upload({"models": [model]})

# ─── 스크립트 실행 시 ───────────────────────
if __name__ == "__main__":
    model2_retrain()

# retrain/icu_congestion_retrain.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import os
import joblib
import shutil, json
import logging
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from catboost import CatBoostRegressor  

from utils.db_loader import get_api_logs_raw
from utils.preprocess import (
    parse_model23_input,
    preprocess  
)

from utils.ncp_client import upload_file_to_ncp


# ─── 환경 설정 ─────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
LOCAL_MODEL_PATH = Path(os.getenv("LOCAL_MODEL3_PATH", "./model/model3.pkl"))
NCP_MODEL_KEY = os.getenv("NCP_MODEL3_KEY", "rmrp-models/model3.pkl")

LOCAL_MODEL_PATH.parent.mkdir(exist_ok=True, parents=True)
ARCHIVE_MODEL_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("ICU_DISCHARGE_RETRAIN")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ─── 모델 저장 + NCP 업로드 ─────────────────────
def save_model_and_upload(model_dict: dict):
    joblib.dump(model_dict, LOCAL_MODEL_PATH)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_path = ARCHIVE_MODEL_DIR / f"icu_discharge_{ts}.pkl"
    shutil.copy(LOCAL_MODEL_PATH, archive_path)

    logger.info(f"[저장] 로컬 모델 → {LOCAL_MODEL_PATH}")
    logger.info(f"[저장] 아카이브 → {archive_path}")

    try:
        upload_file_to_ncp(str(LOCAL_MODEL_PATH), NCP_MODEL_KEY)
        logger.info(f"[NCP] 업로드 완료 → {NCP_MODEL_KEY}")
    except Exception as e:
        logger.error(f"[NCP] 업로드 실패 → {e}")


# ─── 메인 재학습 함수 ───────────────────────
def model3_retrain():
    logger.info("ICU 퇴원 수 예측 모델 재학습 시작")

    raw_df = get_api_logs_raw(days=1)
    if raw_df.empty:
        logger.warning("병상 API 로그 데이터가 없습니다.")
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

    # ── 1. 피처 및 타깃 생성 ───────────────────
    df["total_beds"] = df[["embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"]].sum(axis=1)
    df["target_discharges"] = df["dschCct"]  # ICU 퇴원 수 예측

    y = df.pop("target_discharges")

    # ── 2. 전처리 ───────────────────────────────
    X = preprocess(df)
    if X is None or X.empty:
        logger.error("[preprocess] 반환된 X가 None 또는 비어있습니다. 재학습 중단")
        return  # 이거 꼭 있어야 함
    cat_idx = [X.columns.get_loc("ward_code")]

    # ── 3. 모델 학습 ────────────────────────────
    model = CatBoostRegressor(
        depth=6,
        iterations=400,
        learning_rate=0.07,
        cat_features=cat_idx,
        loss_function="RMSE",
        random_state=42,
        verbose=False
    )
    model.fit(X, y)

    save_model_and_upload({"models": [model]})

# ─── 실행 ─────────────────────────────
if __name__ == "__main__":
    model3_retrain()
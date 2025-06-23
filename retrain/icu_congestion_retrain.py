# retrain/icu_congestion_retrain.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os
import joblib
import shutil
import logging, json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from catboost import CatBoostClassifier

from utils.db_loader import get_api_logs_raw  # 새로 추가한 함수
from utils.preprocess import (
    parse_model23_input,
    preprocess
)

# ─── 환경 설정 ─────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
MODEL_PATH = ROOT / "model" / "model2.pkl"
MODEL_PATH.parent.mkdir(exist_ok=True, parents=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
            logger.warning(f"⚠️ JSON 파싱 실패: {e}")
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

    # ── 5. 저장 및 아카이브 ─────────────────────
    joblib.dump({"models": [model]}, MODEL_PATH)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_path = ARCHIVE_MODEL_DIR / f"icu_congestion_{ts}.pkl"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(MODEL_PATH, archive_path)

    logger.info(f"재학습 완료: {MODEL_PATH}")
    logger.info(f"아카이브 저장 완료: {archive_path}")

# ─── 스크립트 실행 시 ───────────────────────
if __name__ == "__main__":
    model2_retrain()

# retrain/icu_congestion_retrain.py

import os
import pickle
import shutil
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ─── 환경 설정 ─────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DATABASE_URL      = os.getenv("DATABASE_URL")
# ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
engine            = create_engine(DATABASE_URL, future=True)

# ─── 컬럼 매핑 ─────────────────
from utils.column_mapping import COLUMN_MAPPING
from utils.preprocess import preprocess


MODEL_DIR  = ROOT / "model"
MODEL_PATH = MODEL_DIR / "icu_congestion.pkl"
MODEL_DIR.mkdir(exist_ok=True, parents=True)

def fetch_log_ctnt(days: int) -> pd.DataFrame:
    sql = """
    SELECT ctnt
      FROM rmrp_portal.tb_api_log
     WHERE req_res = 'REQ'
       AND reg_dtm >= NOW() - INTERVAL :d DAY
       AND com_src_cd = 'CMC03'
    """
    return pd.read_sql(text(sql), engine, params={"d": days})

def model2_retrain():
    # ── 1) 최근 1일치 로그 파싱 ──
    raw_ctnts = fetch_log_ctnt(days=1)
    records = []
    for ct in raw_ctnts["ctnt"]:
        try:
            j = json.loads(ct)
        except json.JSONDecodeError:
            continue
        rt = datetime.strptime(j["trasNo"], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        for info in j.get("ptrmInfo", []):
            for pt in info.get("ptntDtlsCtrlAllLst", []):
                for ward in pt.get("wardLst", []):
                    records.append({
                        "wardCd":      ward.get("wardCd"),
                        "embdCct":     ward.get("embdCct",0),
                        "dschCct":     ward.get("dschCct",0),
                        "useSckbCnt":  ward.get("useSckbCnt",0),
                        "admsApntCct": ward.get("admsApntCct",0),
                        "chupCct":     ward.get("chupCct",0),
                        "record_time": rt,
                    })
    df = pd.DataFrame(records)
    if df.empty:
        print("No data to retrain.")
        return

    # ── 2) 7일 전 평균 점유율 ──
    hist7 = (
        df.assign(total=lambda x: x.embdCct + x.dschCct + x.useSckbCnt + x.admsApntCct + x.chupCct)
          .eval("occ_rate = embdCct / total")
          .groupby("wardCd")["occ_rate"]
          .mean()
          .rename("occ_rate_7d_ago")
          .reset_index()
    )
    df = df.merge(hist7, on="wardCd", how="left")

    # ── 3) total_beds 계산 ──
    df["total_beds"] = df.embdCct + df.dschCct + df.useSckbCnt + df.admsApntCct + df.chupCct
    df.drop(columns=["embdCct","dschCct","useSckbCnt","admsApntCct","chupCct"], inplace=True)

    # ── 4) 컬럼 매핑 ──
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    # ── 5) 타깃 생성 ──
    df["congestion_flag"] = (df.occupied_beds / df.total_beds > 0.9).astype(int)
    y = df.pop("congestion_flag")

    # ── 6) 전처리 및 학습 ──
    X = preprocess(df)
    from catboost import CatBoostClassifier
    cat_idx = [X.columns.get_loc("ward_code")]
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

    # ── 7) 저장 및 아카이브 ──
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
    pickle.dump(model, tmp); tmp.flush()
    MODEL_PATH.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(tmp.name, MODEL_PATH)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    (ARCHIVE_MODEL_DIR / f"icu_congestion_{ts}.pkl").parent.mkdir(exist_ok=True, parents=True)
    shutil.copy(MODEL_PATH, ARCHIVE_MODEL_DIR / f"icu_congestion_{ts}.pkl")

    print("ICU Congestion retrain success:", MODEL_PATH)

if __name__ == "__main__":
    retrain_icu_congestion()

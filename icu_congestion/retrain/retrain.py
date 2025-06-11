# MODEL_SERVICE/icu_congestion/retrain/retrain.py

import os, pickle, shutil, tempfile, json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ─────────── .env 로드 ───────────
ROOT = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DATABASE_URL      = os.getenv("DATABASE_URL")
ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR","./data/archive/models"))
engine            = create_engine(DATABASE_URL, future=True)

# ─────────── 입력 피처 매핑 사전 ───────────
from icu_congestion.utils.column_mapping import COLUMN_MAPPING

def fetch_log_ctnt(days: int) -> pd.DataFrame:
    """
    tb_api_log.ctnt에서 최근 days일간 REQ 로그만 추출
    (로그 타임스탬프 칼럼: reg_dtm)
    """
    sql = """
    SELECT ctnt
    FROM rmrp_portal.tb_api_log
    WHERE req_res = 'REQ'
      AND reg_dtm >= NOW() - INTERVAL :d DAY
      AND com_src_cd = 'CMC03'
    """
    return pd.read_sql(text(sql), engine, params={"d": days})

def retrain_icu_congestion():
    from icu_congestion.retrain.utils import preprocess

    MODEL_DIR  = ROOT / "icu_congestion" / "model"
    MODEL_PATH = MODEL_DIR / "catboost_model.pkl"
    MODEL_DIR.mkdir(exist_ok=True, parents=True)

    # ── 1) 최근 1시간치 API 로그에서 REQ ctnt JSON 파싱 ──
    raw_ctnts = fetch_log_ctnt(days=1)    # retrain 주기에 맞춰 days 조절
    records = []
    for ct in raw_ctnts:
        try:
            j = json.loads(ct)
        except json.JSONDecodeError:
            continue
        rt = datetime.strptime(j["trasNo"], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        for info in j.get("ptrmInfo", []):
            for pt in info.get("ptntDtlsCtrlAllLst", []):
                for ward in pt.get("wardLst", []):
                    records.append({
                        "wardCd":       ward.get("wardCd"),
                        "embdCct":      ward.get("embdCct", 0),
                        "dschCct":      ward.get("dschCct", 0),
                        "useSckbCnt":   ward.get("useSckbCnt", 0),
                        "admsApntCct":  ward.get("admsApntCct", 0),
                        "chupCct":      ward.get("chupCct", 0),
                        "record_time":  rt,
                    })
    df = pd.DataFrame(records)
    if df.empty:
        print("No data to retrain.")
        return

    # ── 2) 과거 로그에서 7일 평균 점유율 계산(같은 방식으로) ──
    hist7 = df.groupby("wardCd").apply(
        lambda g: (g["embdCct"] / (g["embdCct"]+g["dschCct"]+g["useSckbCnt"]+g["admsApntCct"]+g["chupCct"])).mean()
    ).rename("occ_rate_7d_ago").reset_index()
    df = df.merge(hist7, on="wardCd", how="left")

    # ── 3) total_beds 계산 ──
    df["total_beds"] = (
          df["embdCct"]
        + df["dschCct"]
        + df["useSckbCnt"]
        + df["admsApntCct"]
        + df["chupCct"]
    )
    df.drop(columns=["embdCct","dschCct","useSckbCnt","admsApntCct","chupCct"], inplace=True)

    # ── 4) 입력 피처 매핑 ──
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    # ── 5) 불필요 컬럼 삭제, 타깃 분리 ──
    df.drop(columns=["ratio_male_female","ratio_elder"], errors="ignore", inplace=True)
    df["congestion_flag"] = (df["occupied_beds"] / df["total_beds"] > 0.9).astype(int)
    y = df.pop("congestion_flag")

    # ── 6) 전처리 & 모델 학습 ──
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

    # ── 7) 저장 archive ──
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
    pickle.dump(model, tmp); tmp.flush()
    shutil.move(tmp.name, MODEL_PATH)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    shutil.copy(MODEL_PATH, ARCHIVE_MODEL_DIR / f"icu_congestion_{ts}.pkl")

    print("재학습 성공 ! :", MODEL_PATH)

if __name__ == "__main__":
    retrain_icu_congestion()

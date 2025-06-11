# MODEL_SERVICE/icu_discharge/api/main.py

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
from datetime import datetime, timezone
import pickle, pandas as pd
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# ───────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
MODEL_RELOAD_INTERVAL = int(os.getenv("MODEL_RELOAD_INTERVAL", "10"))

ROOT_DIR         = Path(__file__).resolve().parent.parent
DISCH_MODEL_PATH = ROOT_DIR / "icu_discharge" / "model" / "current_model.pkl"
icu_disch_model  = None
dis_mtime        = 0.0

COLUMN_MAPPING = {
    "wardCd":          "ward_code",
    "wardCd + embdCct + dschCct + useSckbCnt + admsApntCct + chupCct":   "total_beds",
    "embdCct":  "occupied_beds",
    "dschCct": "discharges_24h",
    "admsApntCct": "admissions_24h",
    "occ_rate_last_day": "occ_rate_1d_ago",
    "occ_rate_last_week":"occ_rate_7d_ago",
    "ratio_male_female": "sex_ratio",
    "ratio_elder":       "age_band_ratio"
}

class ICUStatusRow(BaseModel):
    icu_code: str
    total_bed_count: int
    current_occupied: int
    recent_discharges: int
    recent_admissions: int
    occ_rate_last_day: float
    occ_rate_last_week: float
    ratio_male_female: float
    ratio_elder: float

def _hot_reload():
    global icu_disch_model, dis_mtime
    try:
        new_mtime = DISCH_MODEL_PATH.stat().st_mtime
        if new_mtime != dis_mtime:
            with open(DISCH_MODEL_PATH, "rb") as f:
                icu_disch_model = pickle.load(f)
            dis_mtime = new_mtime
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Model not found: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    _hot_reload()
    yield

app = FastAPI(title="ICU Discharge API", version="1.0.0", lifespan=lifespan)

from icu_discharge.retrain.utils import preprocess as preprocess_dis

@app.get("/health")
def health():
    return {"status": "ok", 
            "time": datetime.now(timezone.utc).isoformat()}

@app.post("/icu/discharge/predict", tags=["prediction"])
def predict_discharges(rows: List[ICUStatusRow]):
    _hot_reload()

    df = pd.DataFrame([r.dict() for r in rows])
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    df["free_beds"]        = df["total_beds"] - df["occupied_beds"]
    df["occ_rate"]         = df["occupied_beds"] / df["total_beds"]
    df["occupancy_change"] = (
        df["occupied_beds"] - df["discharges_24h"] + df["admissions_24h"]
    )

    X     = preprocess_dis(df)
    dcnt  = icu_disch_model.predict(X).round().astype(int).tolist()
    today = datetime.utcnow().date().isoformat()
    return {"results": [{"date": today, "expected_discharges": n} for n in dcnt]}

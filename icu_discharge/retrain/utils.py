# MODEL_SERVICE/icu_discharge/retrain/utils.py

from pathlib import Path
import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler

NUM_COLS = [
    "free_beds",
    "occ_rate",
    "occupancy_change",
    "discharges_24h",
    "admissions_24h",
    "occ_rate_1d_ago",
    "occ_rate_7d_ago",
    "sex_ratio",
    "age_band_ratio",
]
CAT_COLS = ["ward_code"]

_SCALER_PATH = Path(__file__).with_name("scaler.pkl")

def fit_scaler(df: pd.DataFrame):
    scaler = StandardScaler().fit(df[NUM_COLS])
    with open(_SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

def _load_scaler():
    if not _SCALER_PATH.exists():
        raise FileNotFoundError(f"Scaler not found: {_SCALER_PATH}")
    with open(_SCALER_PATH, "rb") as f:
        return pickle.load(f)

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    scaler = _load_scaler()
    df = df.copy()
    df.loc[:, NUM_COLS] = scaler.transform(df[NUM_COLS])
    return df[NUM_COLS + CAT_COLS]

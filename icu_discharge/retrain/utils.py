import pandas as pd

NUM_COLS = [
    "free_beds",
    "total_beds",
    "occupied_beds",
    "discharges_24h",
    "admissions_24h",
    # discharge 모델에 필요한 피처 추가
]

CAT_COLS = ["ward_code"]

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df[NUM_COLS + CAT_COLS]

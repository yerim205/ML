# MODEL_SERVICE/icu_congestion/retrain/utils.py

import pandas as pd

# 모델 학습에 사용된 피처명 리스트
NUM_COLS = [
    "free_beds",
    "total_beds",
    "occupied_beds",
    "discharges_24h",
    "admissions_24h",
    "occ_rate_1d_ago",
    "occ_rate_7d_ago",
]
CAT_COLS = ["ward_code"]

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    retrain·예측 공통 전처리
    1) DataFrame 복사
    2) NUM_COLS + CAT_COLS 순서로 피처만 추출하여 반환
    """
    df = df.copy()
    return df[NUM_COLS + CAT_COLS]

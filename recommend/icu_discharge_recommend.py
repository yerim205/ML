# recommend/icu_discharge_recommend.py

import os
import pandas as pd
from pathlib import Path
from joblib import load
from datetime import datetime
from utils.column_mapping import COLUMN_MAPPING
from utils.preprocess import preprocess

ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "model" / "model3.pkl"

def recommend(data: dict) -> dict:
    model_data = load(MODEL_PATH)

    cat_model = model_data['cat_model']    # 예측 모델
    scaler = model_data['scaler']          # 필요 시 사용
    num_imputer = model_data['num_imputer']# 필요 시 사용
    num_cols = model_data['num_cols']      # 수치형 컬럼 리스트
    cat_col = model_data['cat_col']        # 범주형 컬럼 리스트

    df = pd.DataFrame([data])
    
    # total_beds 계산
    required_cols = ['embdCct','dschCct','useSckbCnt','admsApntCct','chupCct']
    if all(col in df.columns for col in required_cols):
        df['total_beds'] = df[required_cols].sum(axis=1)

    # 컬럼명 매핑 및 전처리
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    X = preprocess(df)

    # 필요한 전처리 (예: 수치형 결측값 처리 및 스케일링)
    # 예시 (모델 저장 시와 동일한 전처리 순서 적용)
    X[num_cols] = num_imputer.transform(X[num_cols])
    X[num_cols] = scaler.transform(X[num_cols])

    # 예측 실행
    pred_value = cat_model.predict(X)[0]

    return {
        'prediction': float(pred_value),
        'timestamp': datetime.now().isoformat()
    }

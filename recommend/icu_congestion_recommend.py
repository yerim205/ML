# # recommend/icu_congestion_recommend.py
# import os
# import pandas as pd
# from pathlib import Path
# from joblib import load
# from datetime import datetime

# from recommend.hybrid_scheduler import HybridScheduler

# from utils.column_mapping import COLUMN_MAPPING
# from utils.preprocess import preprocess

# ROOT = Path(__file__).parent.parent
# MODEL_PATH = ROOT / "model/model2.pkl"

# def recommend(data: dict) -> dict:
#     """ICU 병동 혼잡도 예측 API"""
#     # 모델 로드
#     model = load(MODEL_PATH)
#     result = model.recommend(data)

    
#     # 입력 데이터 처리
#     df = pd.DataFrame([data])
#     # 침상 수 계산
#     required_cols = ['embdCct','dschCct','useSckbCnt','admsApntCct','chupCct']
#     if all(col in df.columns for col in required_cols):
#         df['total_beds'] = df[required_cols].sum(axis=1)
    
#     # 컬럼 매핑 및 전처리
#     df.rename(columns=COLUMN_MAPPING, inplace=True)
#     X = preprocess(df)
    
#     # 예측 실행
#     pred = model.predict(X)[0]
#     proba = model.predict_proba(X)[0][1]
    
#     return {
#         'prediction': int(pred),
#         'probability': float(proba),
#         'timestamp': datetime.now().isoformat()
#     }
from pathlib import Path
from datetime import datetime
import pandas as pd

from utils.column_mapping import COLUMN_MAPPING
from utils.preprocess import preprocess

ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "model/model2.pkl"

# 모델을 한 번만 로드하는 전역 변수
model = None

def load_model():
    global model
    if model is None:
        from joblib import load
        model = load(MODEL_PATH)

def recommend(data: dict) -> dict:
    """ICU 병동 혼잡도 예측 API"""
    load_model()

    # HybridScheduler 객체라면 recommend 메서드 사용
    if hasattr(model, 'recommend') and callable(getattr(model, 'recommend')):
        return model.recommend(data)

    # 일반 sklearn 모델일 경우
    df = pd.DataFrame([data])
    required_cols = ['embdCct','dschCct','useSckbCnt','admsApntCct','chupCct']
    if all(col in df.columns for col in required_cols):
        df['total_beds'] = df[required_cols].sum(axis=1)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    X = preprocess(df)
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0][1]
    return {
        'prediction': int(pred),
        'probability': float(proba),
        'timestamp': datetime.now().isoformat()
    }

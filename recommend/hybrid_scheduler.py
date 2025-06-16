# recommend/hybrid_scheduler.py

import pandas as pd
from joblib import dump, load
from datetime import datetime

class HybridScheduler:
    def __init__(self, model_path):
        self.model_path = str(model_path)
        self.model = load(self.model_path)
        self.feedback_log = []

    def update_feedback(self, feedback_list):
        self.feedback_log.extend(feedback_list)
        # 실제 모델 업데이트 로직이 필요한 경우 여기에 추가

    def recommend(self, data: dict) -> dict:
        # 모델별로 전처리/추천 로직이 다를 수 있으니, 필요하다면 클래스 상속으로 분리 가능
        df = pd.DataFrame([data])
        required_cols = ['embdCct', 'dschCct', 'useSckbCnt', 'admsApntCct', 'chupCct']
        if all(col in df.columns for col in required_cols):
            df['total_beds'] = df[required_cols].sum(axis=1)
        # 전처리
        from utils.column_mapping import COLUMN_MAPPING
        from utils.preprocess import preprocess
        df.rename(columns=COLUMN_MAPPING, inplace=True)
        X = preprocess(df)
        pred = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)[0][1]
        return {
            'prediction': int(pred),
            'probability': float(proba),
            'timestamp': datetime.now().isoformat()
        }

    def save(self, path=None):
        if path is None:
            path = self.model_path
        dump(self, path)

    @staticmethod
    def load(path):
        return load(path)

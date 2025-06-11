# ~/Desktop/model_service/test_dummy.py

import pickle
import numpy as np
from catboost import Pool

# 1) 모델 로드
model = pickle.load(open("icu_congestion/model/catboost_model.pkl","rb"))

# 2) 더미 피처 벡터 생성
# 순서: free_beds, total_beds, occupied_beds, discharges_24h, admissions_24h,
#       occ_rate_1d_ago, occ_rate_7d_ago, ward_code(숫자 코드)
feat = [
    5,    # free_beds
    20,   # total_beds
    15,   # occupied_beds
    2,    # discharges_24h
    1,    # admissions_24h
    0.7,  # occ_rate_1d_ago
    0.75, # occ_rate_7d_ago
    0,
    0     # ward_code (정수 코드)
]

X = np.array([feat], dtype=float)

# 3) Pool 생성 (수치형만)
pool = Pool(data=X)

# 4) 예측
preds = model.predict(pool).astype(int).tolist()
print("더미 피처 예측 결과:", preds)

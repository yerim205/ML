# save_model.py
from joblib import dump
from recommend.hybrid_scheduler import HybridScheduler  # 반드시 import로 불러오기

model = HybridScheduler()
dump(model, "model/model1.pkl")
# recommend/icu_congestion_recommend.py
from pathlib import Path
from joblib import load
from datetime import datetime

from utils.db_loader import (
    get_realtime_data_for_today,
    get_realtime_data_for_days_ago
)
from utils.preprocess import (
    parse_model23_input,
    generate_model2_features
)

# ─── 스마트 모델 로드 경로 설정 ───
ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "model" / "model2.pkl"

# ─── ICU 혼잡도 예측 API 함수 ───
def recommend(_: dict) -> dict:
    """
    ICU 혼잡도 예측 전처 API

    Returns:
    - {
        "prediction": 예측 범위,
        "probability": 가능성,
        "timestamp": 시간
      }
    """
    # (1) 데이터 로드
    today_jsons = get_realtime_data_for_today()
    lag1_jsons = get_realtime_data_for_days_ago(1)
    lag7_jsons = get_realtime_data_for_days_ago(7)

    # (2) 패시 및 DataFrame 변환
    df_today = parse_model23_input(today_jsons)
    df_lag1 = parse_model23_input(lag1_jsons)
    df_lag7 = parse_model23_input(lag7_jsons)

    if df_today.empty or df_lag1.empty or df_lag7.empty:
        return {
            "error": "일별 데이터에 의미있는 기본 정보가 보장되지 않았습니다.",
            "timestamp": datetime.now().isoformat()
        }

    # (3) 피처 생성
    target_date = datetime.now()
    X = generate_model2_features(df_today, df_lag1, df_lag7, target_date)

    # (4) 모델 로드
    model_data = load(MODEL_PATH)
    cat_model = model_data['cat_model']

    # (5) 예측
    pred = cat_model.predict(X)[0]
    proba = cat_model.predict_proba(X)[0][1]

    return {
        "prediction": int(pred),
        "probability": float(proba),
        "timestamp": datetime.now().isoformat()
    }

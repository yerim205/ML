#recommend/icu_congestion.py
from pathlib import Path
from joblib import load
from datetime import datetime
import pandas as pd
import traceback
from catboost import Pool
import numpy as np  

from utils.ncp_client import download_file_from_ncp

import logging
logger = logging.getLogger(__name__)

from utils.db_loader import (
    get_realtime_data_for_today,
    get_realtime_data_for_days_ago
)
from utils.preprocess import (
    parse_model23_input,
    generate_model2_features
)

# ROOT = Path(__file__).parent.parent
# MODEL_PATH = ROOT / "model" / "model2.pkl"

ROOT = Path(__file__).parent.parent
LOCAL_MODEL_PATH = ROOT / "model" / "model2.pkl"
NCP_MODEL_KEY = "rmrp-models/model2.pkl" 

def auto_congestion_recommend(_: dict) -> dict:
    try:
        # ─── (1) 모델 로딩 ─────────────────────
        if not LOCAL_MODEL_PATH.exists():
            print("모델이 로컬에 없음 → NCP에서 다운로드 중")
            download_file_from_ncp(NCP_MODEL_KEY, str(LOCAL_MODEL_PATH))

        model_data = load(LOCAL_MODEL_PATH)

        model_list = model_data.get("models")
        if not model_list or not isinstance(model_list, list):
            raise ValueError("'models' 키에 유효한 모델 리스트가 없습니다.")

        model = model_list[0]

        # ─── (2) 데이터 수집 ─────────────────────
        today_jsons = get_realtime_data_for_today()
        lag1_jsons = get_realtime_data_for_days_ago(1)
        lag7_jsons = get_realtime_data_for_days_ago(7)
        print(f"today={len(today_jsons)}, lag1={len(lag1_jsons)}, lag7={len(lag7_jsons)}")

        # ─── (3) 전처리 ─────────────────────────
        df_today = pd.DataFrame([row for d in today_jsons for row in parse_model23_input(d)])
        df_lag1 = pd.DataFrame([row for d in lag1_jsons for row in parse_model23_input(d)])
        df_lag7 = pd.DataFrame([row for d in lag7_jsons for row in parse_model23_input(d)])
        print(f"DataFrame shapes: today={df_today.shape}, lag1={df_lag1.shape}, lag7={df_lag7.shape}")

<<<<<<< HEAD
        # ─── (4) 유효성 검사 ─────────────────────
        if df_today.empty or df_lag1.empty or df_lag7.empty:
            # 2025-06-24(화) -> 있는거 검사해서 1일전 7일전 데이터 대체 (임시)
            # <ex> today 데이터만 있고 1, 7일 전 데이터가 없으면 today 데이터를 1, 7일 전 데이터로 사용
            # <ex> 1일 전 데이터만 있고 today, 7일 전 데이터가 없으면 1일 전 데이터를 today, 7일 전 데이터로 사용
            # <ex> today, 1일 전 데이터만 있고 7일 전 데이터가 없으면 1일 전 데이터를 7일 전 데이터로 사용(과거 데이터는 과거와 가장 가까운 시점의 데이터로 사용)
=======
        # # ─── (4) 유효성 검사 ─────────────────────
        # if df_today.empty or df_lag1.empty or df_lag7.empty:
        #     return {
        #         "success": False,
        #         "result": {
        #             "message": "입력 데이터 중 하나 이상이 비어 있습니다.",
        #             "prediction": None
        #         }
        #     }
        # ─── (4) 유효성 검사 및 백업 ─────────────────────
# 조기 리턴 없이, 각 df 비었을 때 대체하는 구조
        if df_today.empty and df_lag1.empty and df_lag7.empty:
>>>>>>> 4d830c42 (.)
            return {
        "success": False,
        "result": {
            "message": "today, lag1, lag7 데이터 모두 비어 있음 → 예측 불가",
            "prediction": None
        }
    }

# 있으면 최대한 대체
        if df_today.empty:
            if not df_lag1.empty:
                logger.warning("today 없음 → lag1으로 대체")
                f_today = df_lag1.copy()
            elif not df_lag7.empty:
                logger.warning("today 없음 → lag7으로 대체")
                df_today = df_lag7.copy()

        if df_lag1.empty:
            if not df_today.empty:
                logger.warning("lag1 없음 → today로 대체")
                df_lag1 = df_today.copy()
            elif not df_lag7.empty:
                logger.warning("lag1 없음 → lag7으로 대체")
                df_lag1 = df_lag7.copy()

        if df_lag7.empty:
            if not df_lag1.empty:
                logger.warning("lag7 없음 → lag1으로 대체")
                df_lag7 = df_lag1.copy()
            elif not df_today.empty:
                logger.warning("lag7 없음 → today로 대체")
                df_lag7 = df_today.copy()

        # ─── (5) 피처 생성 ──────────────────────
        target_date = datetime.now()
        X = generate_model2_features(df_today, df_lag1, df_lag7, target_date)
        print("생성된 피처 (X):\n", X.head())

        # ─── (6) 예측 ───────────────────────────
        pool = Pool(X)
        pred_value = model.predict(pool)[0]
        print("예측 결과:", pred_value)

        # ─── (7) 예측값 처리 및 응답 구성 ───────
        if isinstance(pred_value, (int, float,np.integer, np.floating)):
            pred = float(pred_value)
            prediction = int(pred) if pred.is_integer() else round(pred, 3)
        else:
            raise ValueError("예측 결과가 숫자형이 아닙니다.")

        return {
            "success": True,
            "result": {
                "prediction": prediction
            }
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "result": {
                "message": f"혼잡도 예측 오류: {str(e)}",
                "prediction": None
            }
        }

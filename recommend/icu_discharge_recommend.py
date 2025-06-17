#recommend/icu_discharge_recommend.py 
#6월 17일 수정 중
from pathlib import Path
from joblib import load
import pandas as pd
from datetime import datetime
from utils.preprocess import parse_model23_input
from utils.db_loader import get_realtime_data_for_today

# 모델 경로 설정
ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "model" / "model3.pkl"

# 모델 로딩 함수
def load_discharge_model():
    model_data = load(MODEL_PATH)
    return (
        model_data["cat_model"],     # 예측 모델
        model_data["scaler"],        # 스케일러
        model_data["num_imputer"],   # 결측값 대치기
        model_data["num_cols"],      # 수치형 컬럼 리스트
        model_data["cat_col"]        # 범주형 컬럼 리스트
    )

# 아침/오후 입원 비율 요약 함수
def summarize_admissions_by_time(realtime_jsons: list[dict], ward_code: str) -> dict:
    morning = 0
    afternoon = 0

    for data in realtime_jsons:
        timestamp = data.get("_timestamp")
        if not timestamp:
            continue

        wards = [
            w for ptrm in data.get("ptrmInfo", [])
            for ptnt in ptrm.get("ptntDtlsCtrlAllLst", [])
            for w in ptnt.get("wardLst", [])
            if w.get("wardCd") == ward_code
        ]

        if not wards:
            continue

        hour = timestamp.hour
        if 6 <= hour < 12:
            morning += 1
        elif 12 <= hour < 18:
            afternoon += 1

    total = morning + afternoon
    return {
        "morning_ratio": morning / total if total else 0.5,
        "afternoon_ratio": afternoon / total if total else 0.5
    }

# 예측 API 함수
def recommend(input_data: dict) -> dict:
    """
    ICU 전체 퇴원자 수 예측

    Parameters:
    - input_data: {
        "realtime": dict,  # 병상 원시 데이터
        "admissions": int,
        "prev_dis": int,
        "prev_week_dis": int,
        "dow": int,
        "is_weekend": int,
        "ward_code": str
      }

    Returns:
    - {
        "prediction": float,
        "timestamp": str
      }
    """
    # 1. 모델 로딩
    cat_model, scaler, num_imputer, num_cols, cat_col = load_discharge_model()

    # 2. 병상 정보 파싱 및 파생변수 생성
    ward_data = parse_model23_input(input_data["realtime"])
    df = pd.DataFrame(ward_data)
    df = df[df["wardCd"] == input_data["ward_code"]].copy()

    if df.empty:
        raise ValueError("해당 ward_code에 해당하는 병상 데이터가 없습니다.")

    df["total_beds"] = df[["embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"]].sum(axis=1)
    total_beds = df["total_beds"].iloc[0] if not df.empty else 1
    occupancy_rate = df["useSckbCnt"].iloc[0] / total_beds if total_beds > 0 else 0

    # 3. 시간대 기반 입원 비율 계산
    today_data = get_realtime_data_for_today()
    ward_code = input_data["ward_code"]
    latest_ward_data = next(
    (
        d for d in reversed(today_data)
        if any(
            w.get("wardCd") == ward_code
            for ptrm in d.get("ptrmInfo", [])
            for ptnt in ptrm.get("ptntDtlsCtrlAllLst", [])
            for w in ptnt.get("wardLst", [])
        )
         ),
        None
        )
    
    if not latest_ward_data or "_timestamp" not in latest_ward_data:
        raise ValueError("해당 ward_code에 대한 유효한 timestamp가 없습니다.")

    ts = latest_ward_data["_timestamp"]
    dow = ts.weekday()
    is_weekend = int(dow >= 5)

    adm_summary = summarize_admissions_by_time(today_data, input_data["ward_code"])

    # 4. 최종 feature dict 구성
    features = {
        "admissions": input_data["admissions"],
        "prev_dis": input_data["prev_dis"],
        "prev_week_dis": input_data["prev_week_dis"],
        "dow": input_data["dow"],
        "is_weekend": input_data["is_weekend"],
        "ward_code": input_data["ward_code"],
        "occupancy_rate": occupancy_rate,
        "morning_ratio": adm_summary["morning_ratio"],
        "afternoon_ratio": adm_summary["afternoon_ratio"]
    }

    # 5. 피처 필터링 및 전처리
    filtered_features = {
        k: v for k, v in features.items()
        if k in num_cols + cat_col
    }
    df_feat = pd.DataFrame([filtered_features])
    df_feat[num_cols] = num_imputer.transform(df_feat[num_cols])
    df_feat[num_cols] = scaler.transform(df_feat[num_cols])

    # 6. 예측
    pred = cat_model.predict(df_feat)[0]

    return {
        "prediction": float(pred),
        "timestamp": datetime.now().isoformat()
    }

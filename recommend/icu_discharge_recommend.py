# recommend/icu_discharge_recommend.py
import traceback  # ← 추가
from utils.db_loader import (
    get_latest_realtime_data,
    get_latest_realtime_data_for_days_ago,
    safe_get_realtime_data_for_today
)
from utils.preprocess import parse_model23_input
from pathlib import Path
from joblib import load
from datetime import datetime, time
import pandas as pd

# 모델 파일 경로
ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "model" / "model3.pkl"

# 모델 로딩 함수
def load_discharge_model():
    model_data = load(MODEL_PATH)
    return (
        model_data["cat_model"],
        model_data["scaler"],
        model_data["num_imputer"],
        model_data["num_cols"],
        model_data["cat_col"]
    )

# 시간대별 입원 요약 함수
def summarize_admissions_by_time(realtime_jsons: list[dict], ward_code: str) -> dict:
    morning = 0
    afternoon = 0
    for data in realtime_jsons:
        timestamp = data.get("_timestamp")
        if not timestamp:
            continue
        for ptrm in data.get("ptrmInfo", []):
            for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
                for w in ptnt.get("wardLst", []):
                    if w.get("wardCd") == ward_code:
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


def auto_recommend() -> dict:
    try:
        # 1. 모델 로딩
        model, scaler, imputer, num_cols, cat_col = load_discharge_model()

        # 2. 기준 날짜 추출
        latest_json = get_latest_realtime_data()
        base_ts = latest_json.get("_timestamp", datetime.now())
        print("🕒 get_latest_realtime_data 기준 timestamp:", base_ts)

        base_date = base_ts.date()
        print("📅 기준 base_date:", base_date)


        # 3. 오늘/전일/일주일 전 실시간 병상 데이터 로딩
        today_raw = safe_get_realtime_data_for_today()
        lag1_raw = [get_latest_realtime_data_for_days_ago(1)]
        lag7_raw = [get_latest_realtime_data_for_days_ago(7)]

        print("📅 날짜 기준:", base_date)
        print("✅ today_raw 길이:", len(today_raw))
        print("✅ lag1_raw 길이:", len(lag1_raw))
        print("✅ lag7_raw 길이:", len(lag7_raw))

        # 4. 파싱
        today_df = pd.DataFrame([w for d in today_raw for w in parse_model23_input(d)])
        lag1_df = pd.DataFrame([w for d in lag1_raw for w in parse_model23_input(d)])
        lag7_df = pd.DataFrame([w for d in lag7_raw for w in parse_model23_input(d)])

        print("📊 today_df columns:", today_df.columns)
        print("📊 lag1_df columns:", lag1_df.columns)
        print("📊 lag7_df columns:", lag7_df.columns)

        if today_df.empty or "wardCd" not in today_df.columns:
            raise ValueError("❌ today_df가 비어있거나 'wardCd'가 없습니다.")

        # ✅ early return 조건: 이전 데이터 부족 시
        if lag1_df.empty or "wardCd" not in lag1_df.columns:
            return {
                "predictions": [],
                "timestamp": base_ts.isoformat(),
                "warning": "전일 데이터가 부족하여 예측을 수행하지 않았습니다."
            }

        if lag7_df.empty or "wardCd" not in lag7_df.columns:
            return {
                "predictions": [],
                "timestamp": base_ts.isoformat(),
                "warning": "일주일 전 데이터가 부족하여 예측을 수행하지 않았습니다."
            }

        results = []
        for ward_code in today_df["wardCd"].unique():
            print(f"➡️ 예측 시작: {ward_code}")
            ward_rows = today_df[today_df["wardCd"] == ward_code]
            if ward_rows.empty:
                continue

            total_beds = ward_rows[["embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct"]].sum(axis=1).iloc[0]
            occupancy_rate = ward_rows["useSckbCnt"].iloc[0] / total_beds if total_beds else 0

            admissions = ward_rows["admsApntCct"].sum()
            prev_dis = lag1_df[lag1_df["wardCd"] == ward_code]["dschCct"].sum()
            prev_week_dis = lag7_df[lag7_df["wardCd"] == ward_code]["dschCct"].sum()

            dow = base_ts.weekday()
            is_weekend = int(dow >= 5)
            adm_summary = summarize_admissions_by_time(today_raw, ward_code)

            features = {
                "admissions": admissions,
                "prev_dis": prev_dis,
                "prev_week_dis": prev_week_dis,
                "dow": dow,
                "is_weekend": is_weekend,
                "ward_code": ward_code,
                "occupancy_rate": occupancy_rate,
                "morning_ratio": adm_summary["morning_ratio"],
                "afternoon_ratio": adm_summary["afternoon_ratio"]
            }

            filtered = {k: v for k, v in features.items() if k in num_cols + cat_col}
            X = pd.DataFrame([filtered])

            missing_cols = [col for col in num_cols if col not in X.columns]
            if missing_cols:
                raise ValueError(f"❌ 수치형 컬럼 누락: {missing_cols}")

            X[num_cols] = imputer.transform(X[num_cols])
            X[num_cols] = scaler.transform(X[num_cols])

            pred = model.predict(X)[0]
            results.append({
                "ward_code": ward_code,
                "prediction": float(pred)
            })

        return {
            "predictions": results,
            "timestamp": base_ts.isoformat()
        }

    except Exception as e:
        raise ValueError(f"자동 예측 오류: {e}")

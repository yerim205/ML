#recommend/icu_discharge_recommend.py
from utils.db_loader import (
    get_latest_realtime_data,
    get_latest_realtime_data_for_days_ago,
    safe_get_realtime_data_for_today,
)
from utils.preprocess import parse_model23_input
from pathlib import Path
from joblib import load
from datetime import datetime
from catboost import Pool
import pandas as pd

from utils.ncp_client import download_file_from_ncp

# ─── 모델 경로 상수 ─────────────────────────
# ROOT = Path(__file__).parent.parent
# MODEL_PATH = ROOT / "model" / "model3.pkl"
ROOT = Path(__file__).parent.parent
LOCAL_MODEL_PATH = ROOT / "model" / "model3.pkl"
NCP_MODEL_KEY = "rmrp-models/model3.pkl"  

# ─── 모델 로딩 ──────────────────────────────
def load_discharge_model():
    if not LOCAL_MODEL_PATH.exists():
        print("로컬에 model3 없음 → NCP에서 다운로드 중...")
        download_file_from_ncp(NCP_MODEL_KEY, str(LOCAL_MODEL_PATH))

    model_data = load(LOCAL_MODEL_PATH)
    return (
        model_data["cat_model"],
        model_data["scaler"],
        model_data["num_imputer"],
        model_data["num_cols"],
        model_data["cat_col"]
    )

# ─── 시간대별 입원 요약 ─────────────────────
def summarize_admissions_by_time(realtime_jsons: list[dict], ward_code: str) -> dict:
    morning = afternoon = 0
    for data in realtime_jsons:
        ts = data.get("_timestamp")
        if not ts: continue
        for ptrm in data.get("ptrmInfo", []):
            for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
                for w in ptnt.get("wardLst", []):
                    if w.get("wardCd") == ward_code:
                        hour = ts.hour
                        if 6 <= hour < 12: morning += 1
                        elif 12 <= hour < 18: afternoon += 1
    total = morning + afternoon
    return {
        "morning_ratio": morning / total if total else 0.5,
        "afternoon_ratio": afternoon / total if total else 0.5
    }

# ─── 메인 자동 추천 로직 ─────────────────────
def auto_recommend() -> dict:
    try:
        model, scaler, imputer, num_cols, cat_col = load_discharge_model()
        cat_col = [cat_col] if isinstance(cat_col, str) else cat_col
        cat_col = [c for c in cat_col if c not in num_cols]

        # 1. 기준 날짜 및 데이터 로딩
        base_ts = get_latest_realtime_data().get("_timestamp", datetime.now())
        base_date = base_ts.date()
        today_raw = safe_get_realtime_data_for_today()
        lag1_raw = get_latest_realtime_data_for_days_ago(1, base_ts)
        lag7_raw = get_latest_realtime_data_for_days_ago(7, base_ts)

        # 2. 파싱 후 DataFrame 구성
        today_df = pd.DataFrame([w for d in today_raw for w in parse_model23_input(d)])
        lag1_df = pd.DataFrame([w for d in [lag1_raw] for w in parse_model23_input(d)])
        lag7_df = pd.DataFrame([w for d in [lag7_raw] for w in parse_model23_input(d)])

        if today_df.empty or "wardCd" not in today_df:
            raise ValueError("today_df가 비어있거나 'wardCd'가 없습니다.")
        if lag1_df.empty or "wardCd" not in lag1_df:
            return {"predictions": [], "warning": "전일 데이터 부족"}
        if lag7_df.empty or "wardCd" not in lag7_df:
            return {"predictions": [], "warning": "일주일 전 데이터 부족"}

        results, total_pred = [], 0

        for ward_code in today_df["wardCd"].unique():
            ward_rows = today_df[today_df["wardCd"] == ward_code]
            if ward_rows.empty: continue

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
                "ward_code": str(ward_code),
                "occupancy_rate": occupancy_rate,
                "morning_ratio": adm_summary["morning_ratio"],
                "afternoon_ratio": adm_summary["afternoon_ratio"]
            }

            filtered = {k: v for k, v in features.items() if k in num_cols + cat_col}
            X = pd.DataFrame([filtered])
            cat_col_filtered = [c for c in cat_col if c in X and pd.api.types.is_object_dtype(X[c]) or pd.api.types.is_integer_dtype(X[c])]
            # print("최종 cat_col (실수형 제외):", cat_col_filtered)

            missing_cols = [col for col in num_cols if col not in X.columns]
            if missing_cols:
                raise ValueError(f"수치형 컬럼 누락: {missing_cols}")

            X_vals = scaler.transform(imputer.transform(X[num_cols].values))
            X[num_cols] = X_vals

            # X[num_cols] = imputer.transform(X[num_cols])
            # X[num_cols] = scaler.transform(X[num_cols])
            X[cat_col_filtered] = X[cat_col_filtered].astype(str)

            pool = Pool(X, cat_features=cat_col_filtered)
            pred = float(model.predict(pool)[0])
            results.append({"ward_code": ward_code, "prediction": pred})
            total_pred += pred

        avg_pred = total_pred / len(results) if results else None

        return round(avg_pred,3)
    

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ValueError(f"자동 예측 오류: {str(e)}")

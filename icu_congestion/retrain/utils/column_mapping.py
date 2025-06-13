# icu_congestion/utils/column_mapping.py
# DB 컬럼명 -> 학습용 피처명 매핑 사전
COLUMN_MAPPING = {
    "wardCd":           "ward_code",
    "embdCct":          "occupied_beds",
    "dschCct":          "discharges_24h",
    "admsApntCct":      "admissions_24h",
    # total_beds, occ_rate_last_day, occ_rate_last_week 은 코드 내 계산
}

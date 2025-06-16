# utils/column_mapping.py
COLUMN_MAPPING = {
    # 원본 컬럼명: 변환할 컬럼명
    "wardCd": "ward_code",
    "total_beds": "total_beds",
    "occ_rate_7d_ago": "occupancy_rate_7d_ago"

}

CODE_TO_ICD = {
    "01": "I21",
    "02": "I63",
    "03": "I60",
    "04": "I71",
    "05": "I71",
}

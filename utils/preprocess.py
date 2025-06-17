# utils/preprocess.py
import pandas as pd
# ─── 병동 코드 목록 ─────────────────────────────

MODEL1_WARD_CODES = {
    "100950", "105310", "105380", "106250", "106260", "106280", "106620",
    "107010", "107060", "107210", "107250", "107300", "107420", "112880",
    "113150", "106560"
}

MODEL23_WARD_CODES = {
    "106250", "106260", "106270", "106280", "113870"
}

# ─── 공통 파싱 유틸 ────────────────────────────

def _parse_common_fields(ward: dict) -> dict:
    return {
        "wardCd": ward.get("wardCd"),
        "wardNm": ward.get("wardNm"),
        "embdCct": ward.get("embdCct", 0),
        "dschCct": ward.get("dschCct", 0),
        "useSckbCnt": ward.get("useSckbCnt", 0),
        "admsApntCct": ward.get("admsApntCct", 0),
        "chupCct": ward.get("chupCct", 0),
    }

# ─── 모델 1 전용 ───────────────────────────────

def parse_model1_input(realtime_data: dict) -> list[dict]:
    result = []
    for ptrm in realtime_data.get("ptrmInfo", []):
        for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
            for ward in ptnt.get("wardLst", []):
                if ward.get("wardCd") in MODEL1_WARD_CODES:
                    result.append(_parse_common_fields(ward))
    return result

# ─── 모델 2, 3 전용 ────────────────────────────

def parse_model23_input(realtime_data: dict) -> list[dict]:
    result = []
    for ptrm in realtime_data.get("ptrmInfo", []):
        for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
            for ward in ptnt.get("wardLst", []):
                if ward.get("wardCd") in MODEL23_WARD_CODES:
                    result.append(_parse_common_fields(ward))
    return result

# ─── 모델 2,3용 파생 변수 생성 ────────────────────

def generate_model2_features(df_today: pd.DataFrame, df_lag1: pd.DataFrame, df_lag7: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """
    모델2 입력 생성: 하루치 기준점 데이터와 전일/일주일전 병상 데이터를 활용
    """
    # 병동 기준 merge
    df = df_today.merge(df_lag1[['wardCd', 'useSckbCnt']], on='wardCd', how='left', suffixes=('', '_lag1'))
    df = df.merge(df_lag7[['wardCd', 'useSckbCnt']], on='wardCd', how='left', suffixes=('', '_lag7'))

    # 파생 변수 생성
    df['total_beds'] = df[['embdCct', 'dschCct', 'useSckbCnt', 'admsApntCct', 'chupCct']].sum(axis=1)
    df['free_beds'] = df['embdCct'].fillna(0)
    df['occ_rate'] = df['useSckbCnt'] / df['total_beds'].replace(0, 1)
    df['occ_rate_lag1'] = df['useSckbCnt_lag1'] / df['total_beds'].replace(0, 1)
    df['occ_rate_lag7'] = df['useSckbCnt_lag7'] / df['total_beds'].replace(0, 1)
    df['occupancy_change'] = df['useSckbCnt'] - df['useSckbCnt_lag1']

    # 날짜 기반 변수
    df['is_weekend'] = target_date.weekday() >= 5

    # 필요한 컬럼만 반환
    return df[[
        'wardCd', 'free_beds', 'occ_rate', 'occupancy_change',
        'occ_rate_lag1', 'occ_rate_lag7',
        'is_weekend', 'is_public_holiday', 'month', 'quarter'
    ]].copy()

def generate_model3_features(df_today: pd.DataFrame, df_lag1: pd.DataFrame, df_lag7: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """
    모델3 입력 생성: ICU 퇴원 수 예측용
    """
    df = df_today.copy()

    # 기본 파생 변수
    df['occupancy_rate'] = df['occupied_beds'] / df['total_beds'].replace(0, 1)
    df['morning_ratio'] = df['morning_admissions'] / df['total_admissions'].replace(0, 1)
    df['afternoon_ratio'] = df['afternoon_admissions'] / df['total_admissions'].replace(0, 1)

    # 전일 퇴원 수
    df_prev = df_lag1[['ward_code', 'discharges']].rename(columns={'discharges': 'prev_dis'})
    df = df.merge(df_prev, on='ward_code', how='left')

    # 날짜 정보
    df['dow'] = target_date.weekday()
    df['is_weekend'] = target_date.weekday() >= 5

    # 최종 선택된 컬럼만 추출
    return df[[
        'admissions', 'occupancy_rate', 'prev_dis', 'prev_week_dis',
        'morning_ratio', 'afternoon_ratio', 'dow', 'is_weekend', 'ward_code'
    ]]

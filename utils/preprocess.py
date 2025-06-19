# utils/preprocess.py
import pandas as pd
from datetime import datetime

# ─── 병동 코드 목록 ─────────────────────────────
MODEL1_WARD_CODES = {
    "100950", #"105310", "105380", 
    "106250", "106260", "106280", "106620",
    "107010", "107060", "107210", "107250", "107300", "107420", "112880",
    "113150", "106560"
}

WARD_CD_TO_NAME = {
    "100950": "심혈관 일일입원실",
    # "105310": "응급센터",
    "105380": "응급센터",
    "106250": "내과ICU",
    "106260": "외과ICU",
    "106280": "응급중환자실",
    "106620": "54병동",
    "106560": "53병동",
    "107010": "71병동",
    "107060": "72병동",
    "107210": "75병동",
    "107250": "76병동",
    "107300": "78병동",
    "107420": "83병동",
    "112880": "뇌졸중집중치료실",
    "113150": "69병동",
}

MODEL23_WARD_CODES = ["105380","106250", "106260", "106270", "106280", "113870"]

# ─── 병상 상태 기반 공통 필드 파싱 ─────────────────────────
def parse_bed_status_counts(ward: dict) -> dict:
    """
    ward['trasItemLst']에서 병상 상태 코드별 카운트 계산
    """
    status_counts = {
        "embdCct": 0,       # Y
        "dschCct": 0,       # P
        "admsApntCct": 0,   # A
        "useSckbCnt": 0,    # N, W
        "chupCct": 0        # C
    }

    for item in ward.get("trasItemLst", []):
        code = item.get("ptrmUseDvsnCd")
        if code == "Y":
            status_counts["embdCct"] += 1
        elif code == "P":
            status_counts["dschCct"] += 1
        elif code == "A":
            status_counts["admsApntCct"] += 1
        elif code in {"N", "W"}:
            status_counts["useSckbCnt"] += 1
        elif code == "C":
            status_counts["chupCct"] += 1

    return {
        "wardCd": ward.get("wardCd"),
        "wardNm": ward.get("wardNm"),
        **status_counts
    }

# ─── 모델 1 전용 파서 ─────────────────────────────
def parse_model1_input(realtime_data: dict) -> list[dict]:
    """
    모델 1: 병동 이름 기반 + 중환자실 병상 상태 파싱
    """
    result = []
    for ptrm in realtime_data.get("ptrmInfo", []):
        for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
            for ward in ptnt.get("wardLst", []):
                ward_cd = str(ward.get("wardCd"))
                if ward_cd in MODEL1_WARD_CODES:
                    ward_name = WARD_CD_TO_NAME.get(ward_cd)
                    if not ward_name:
                        continue

                    # 중환자실이면 상태 기반 파싱
                    if ward_cd in MODEL23_WARD_CODES:
                        parsed = parse_bed_status_counts(ward)
                        parsed["ward"] = ward_name  # 모델에서 요구하는 'ward' 컬럼
                    else:
                        parsed = {
                            "ward": ward_name,
                            "embdCct": ward.get("embdCct", 0),
                            "dschCct": ward.get("dschCct", 0),
                            "useSckbCnt": ward.get("useSckbCnt", 0),
                            "admsApntCct": ward.get("admsApntCct", 0),
                            "chupCct": ward.get("chupCct", 0),
                        }
                    result.append(parsed)
    return result


# ─── 모델 2 & 3 전용 파서 ────────────────────────
# def parse_model23_input(realtime_data: dict) -> list[dict]:
#     result = []
#     for ptrm in realtime_data.get("ptrmInfo", []):
#         for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
#             for ward in ptnt.get("wardLst", []):
#                 ward_cd = str(ward.get("wardCd"))
#                 if ward_cd in MODEL23_WARD_CODES:
#                     parsed = parse_bed_status_counts(ward)
#                     print(f"parsed ward ({ward_cd}):", parsed)
#                     result.append(parsed)
#     return result
def parse_model23_input(realtime_data: dict) -> list[dict]:
    print("🛠️ parse_model23_input() 진입")
    results = []
    try:
        for ptrm in realtime_data.get("ptrmInfo", []):
            #print(" ptrmDvsnCd:", ptrm.get("ptrmDvsnCd"))
            for ptnt in ptrm.get("ptntDtlsCtrlAllLst", []):
                for ward in ptnt.get("wardLst", []):
                    ward_cd = str(ward.get("wardCd"))
                    #print("wardCd 탐색:", ward_cd)

                    if ward_cd in MODEL23_WARD_CODES:
                        parsed = parse_bed_status_counts(ward)
                        #print(" 병상 파싱 성공:", parsed)
                        results.append(parsed)
    except Exception as e:
        #print(" parse_model23_input 내부 에러:", e)
        raise e

    return results

# ─── 모델 2 전용 파생 변수 생성 ───────────────────
def generate_model2_features(df_today, df_lag1, df_lag7, target_date):
    df = df_today.copy()
    
    for df_lag, suffix in zip([df_lag1, df_lag7], ['lag1', 'lag7']):
        if not df_lag.empty and 'wardCd' in df_lag.columns:
            df = df.merge(
                df_lag[['wardCd', 'useSckbCnt']],
                on='wardCd',
                how='left',
                suffixes=('', f'_{suffix}')
            )
        else:
            df[f'useSckbCnt_{suffix}'] = 0  # fallback

    df['total_beds'] = df[['embdCct', 'dschCct', 'useSckbCnt', 'admsApntCct', 'chupCct']].sum(axis=1).replace(0, 1)
    df['free_beds'] = df['embdCct'].fillna(0)
    df['occ_rate'] = df['useSckbCnt'] / df['total_beds']
    df['occ_rate_lag1'] = df['useSckbCnt_lag1'] / df['total_beds']
    df['occ_rate_lag7'] = df['useSckbCnt_lag7'] / df['total_beds']
    df['occupancy_change'] = df['useSckbCnt'] - df['useSckbCnt_lag1']
    df['is_weekend'] = int(target_date.weekday() >= 5)

    return df[[
        'wardCd', 'free_beds', 'occ_rate', 'occupancy_change',
        'occ_rate_lag1', 'occ_rate_lag7', 'is_weekend'
    ]].copy()

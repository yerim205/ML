# #top3_transfer_recommned.py
# from pathlib import Path
# from joblib import load
# import pandas as pd
# from recommend.hybrid_scheduler import HybridScheduler
# from utils.preprocess import parse_model1_input

# from utils.db_loader import get_latest_realtime_data
# from recommend.hybrid_scheduler import EDGES_BY_ICD, RAW_PRIORITY_WEIGHTS
# from utils.ncp_client import download_file_from_ncp 


# import os
# import logging
# from io import BytesIO
# from dotenv import load_dotenv

# from utils import ncp_client

# import os
# from dotenv import load_dotenv
# load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


# CODE_TO_ICD = {
#     "01": "I21",
#     "02": "I63",
#     "03": "I60",
#     "04": "I71",
#     "05": "I71",
# }
# #─── 모델 로드 ─────────────────────
# MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"
# model: HybridScheduler = load(MODEL_PATH)

# ROOT = Path(__file__).parent.parent
# LOCAL_MODEL_PATH = ROOT / "model" / "model1.pkl"
# NCP_MODEL_KEY = "rmrp-models/model1.pkl"

# # ─── 모델 로딩 함수 ─────────────────────────
# def load_transfer_model() -> HybridScheduler:
#     if not LOCAL_MODEL_PATH.exists():
#         print("모델1 로컬에 없음 → NCP에서 다운로드 중")
#         download_file_from_ncp(NCP_MODEL_KEY, str(LOCAL_MODEL_PATH))

#     return load(LOCAL_MODEL_PATH)  


# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# # # ─── NCP에서 바로 모델을 로드 ────────────────────
# # def load_model_from_ncp_direct(ncp_key: str):
# #     logger.info(f"NCP에서 모델 직접 다운로드 중: {ncp_key}")
# #     byte_data = ncp_client.get_object_bytes(ncp_key)  # 바이트로 가져오는 함수 구현되어 있어야 함
# #     model_data = load(BytesIO(byte_data))
# #     return model_data


# def auto_transfer_recommend(icd_code: str) -> dict:
#     """
#     실시간 병상 정보 기반 자동 병동 추천
#     - 공병상이 있는 병동 추천
#     - 공병상 없어도 가중치 기반 추천
#     - 최후 fallback: 비어 있는 병동이라도 추천
#     """
#     try:
#         # 1. 실시간 병상 데이터 로딩
#         realtime_json = get_latest_realtime_data()
#         # 2. 병동 데이터 파싱
#         bed_info = parse_model1_input(realtime_json)

#         if not bed_info:
#             return {
#                 "recommended_wards": [],
#                 "message": "실시간 병상 데이터가 없습니다."
#             }

#         df_live = pd.DataFrame(bed_info)
#         df_live["total_beds"] = (
#             df_live["embdCct"] +
#             df_live["dschCct"] +
#             df_live["useSckbCnt"] +
#             df_live["admsApntCct"] +
#             df_live["chupCct"]
#         )

#         df_live = df_live.groupby("ward", as_index=False).sum(numeric_only=True)
#         df_live["occupancy"] = df_live["useSckbCnt"] / df_live["total_beds"].replace(0, 1)

#         print("입력된 병동 목록:", df_live["ward"].unique())
#         print("병상 수 요약:\n", df_live[["ward", "embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct", "total_beds"]])

#         # 3. 모델 기반 추천 시도
#         model = load_transfer_model()
#         # model = model_data
#         ranked = model.recommend(icd=icd_code, df_live=df_live, top_k=3)
#         print("모델 추천 결과:", ranked)
#         print(" >> 추천 후보군 (점수 있는 ward 수):", len(ranked))
#         print(" >> 추천 점수 목록:", ranked)

#         if ranked:
#          return {
#             "recommended_wards": [{"ward": w, "score": round(s, 5)} for w, s in ranked],
#             "icd": icd_code
#             }

# # fallback
#         fallback_df = df_live.sort_values("occupancy").head(3)
#         fallback_result = [
#              {"ward": row["ward"], "score": 0.0}
#              for _, row in fallback_df.iterrows()
#         ]

#         return {
#                "recommended_wards": fallback_result,
#                 "icd": icd_code,
#                 "fallback": True
#           }

#     except Exception as e:
#          raise ValueError(f"자동 전실 추천 오류: {e}")
#top3_transfer_recommned.py
from pathlib import Path
from joblib import load
import pandas as pd
from recommend.hybrid_scheduler import HybridScheduler
from utils.preprocess import parse_model1_input

from utils.db_loader import get_latest_realtime_data
from recommend.hybrid_scheduler import EDGES_BY_ICD, RAW_PRIORITY_WEIGHTS
from utils.ncp_client import download_file_from_ncp 


from utils.preprocess import parse_model1_input, parse_bed_status_counts
from utils.ncp_client import download_file_from_ncp 


import os
import logging
from io import BytesIO
from dotenv import load_dotenv

from utils import ncp_client
from utils.db_loader import get_latest_realtime_data

#─── 모델 로드 ─────────────────────
MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"
model: HybridScheduler = load(MODEL_PATH)

ROOT = Path(__file__).parent.parent
LOCAL_MODEL_PATH = ROOT / "model" / "model1.pkl"
NCP_MODEL_KEY = "rmrp-models/model1.pkl"

# ─── 모델 로딩 함수 ─────────────────────────
def load_transfer_model() -> HybridScheduler:
    if not LOCAL_MODEL_PATH.exists():
        print("모델1 로컬에 없음 → NCP에서 다운로드 중")
        download_file_from_ncp(NCP_MODEL_KEY, str(LOCAL_MODEL_PATH))

    return load(LOCAL_MODEL_PATH)  


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
CODE_TO_ICD = {
    "01": "I21",
    "02": "I63",
    "03": "I60",
    "04": "I71",
    "05": "I71",
}
# ─── 모델 로드 ─────────────────────
MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"
model: HybridScheduler = load(MODEL_PATH)
def auto_transfer_recommend(icd_code: str) -> dict:
    print(f"입력 ICD 코드: {icd_code}")

    try:
        realtime_json = get_latest_realtime_data()
        bed_info = parse_model1_input(realtime_json)
        print(f"▶ 실시간 병상 데이터 수: {len(bed_info)}")

        if not bed_info:
            return {
                "recommended_wards": [],
                "message": "실시간 병상 데이터가 없습니다."
            }

        df_live = pd.DataFrame(bed_info)
        df_live["total_beds"] = (
            df_live["embdCct"] +
            df_live["dschCct"] +
            df_live["useSckbCnt"] +
            df_live["admsApntCct"] +
            df_live["chupCct"]
        )
        df_live = df_live.groupby("ward", as_index=False).sum(numeric_only=True)
        df_live["occupancy"] = df_live["useSckbCnt"] / df_live["total_beds"].replace(0, 1)
        print("▶ 실시간 병동 목록:", df_live["ward"].tolist())

        model = load_transfer_model()
        ranked = model.recommend(icd=icd_code, df_live=df_live, top_k=3)
        print("▶ 모델 추천 결과:", ranked)

        if ranked:
            return {
                "recommended_wards": [{"ward": w, "score": round(s, 5)} for w, s in ranked],
                "icd": icd_code
            }

        # fallback
        fallback_wards = EDGES_BY_ICD.get(icd_code, [])
        print("▶ fallback 병동:", fallback_wards)
        fallback_result = [{"ward": w, "score": 0.0} for w in fallback_wards]

        if fallback_result:
            return {
                "recommended_wards": fallback_result,
                "icd": icd_code,
                "fallback": True
            }

        return {
            "recommended_wards": [],
            "message": "모델 및 fallback 모두 실패",
            "icd": icd_code
        }

    except Exception as e:
        raise ValueError(f"자동 전실 추천 오류: {e}")

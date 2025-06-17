from pathlib import Path
from joblib import load
import pandas as pd
from recommend.hybrid_scheduler import HybridScheduler
from utils.preprocess import parse_model1_input

# ─── 모델 로드 ─────────────────────
MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"
model: HybridScheduler = load(MODEL_PATH)

# ─── 추천 함수 ─────────────────────
def recommend(input_data: dict) -> dict:
    """
    ICU 병상 추천 API

    Parameters:
    - input_data: {
        "dissCd": str,             # 진단 코드 (예: I63)
        "realtimeData": dict,      # 실시간 병상 JSON (원시 형태)
        "topK": int                # 추천 개수 (기본값 3)
      }

    Returns:
    - {
        "recommended_wards": [ {"ward": str, "score": float}, ... ]
      }
    """
    icd_code = input_data["dissCd"]
    realtime_data = input_data.get("realtimeData", {})
    top_k = input_data.get("topK", 3)

    # 병상 정보 파싱
    bed_info_list = parse_model1_input(realtime_data)
    if not bed_info_list:
        return {
            "recommended_wards": [],
            "message": "No valid bed information found."
        }

    df_live = pd.DataFrame(bed_info_list)

    # 추천 실행
    ranked_results = model.recommend(icd=icd_code, df_live=df_live, top_k=top_k)

    # 결과 포맷 정리
    return {
        "recommended_wards": [
            {"ward": ward, "score": round(score, 5)} for ward, score in ranked_results
        ]
    }

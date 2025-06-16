from pathlib import Path
from joblib import load
import pandas as pd
from recommend.hybrid_scheduler import HybridScheduler, make_state_from_df

# 모델 파일 경로
MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"

# 모델 로딩
model: HybridScheduler = load(MODEL_PATH)

def recommend(input_data: dict) -> dict:
    """
    ICU 병상 추천 API

    input_data: {
        "dissCd": str,             # 진단 코드 (ex: I63)
        "bedInfo": list[dict],     # 병동 실시간 정보 DataFrame 형식과 유사한 dict 리스트
        "topK": int                # 추천 개수 (기본값 3)
    }

    return: {
        "recommended_wards": [ {"ward": str, "score": float}, ... ]
    }
    """
    icd_code = input_data["dissCd"]
    bed_info_list = input_data.get("bedInfo", [])
    top_k = input_data.get("topK", 3)

    # 병상 정보 DataFrame으로 변환
    df_live = pd.DataFrame(bed_info_list)

    # 추천 결과 얻기
    ranked_results = model.recommend(icd=icd_code, df_live=df_live, top_k=top_k)

    # 반환 포맷 정리
    return {
        "recommended_wards": [
            {"ward": ward, "score": round(score, 5)} for ward, score in ranked_results
        ]
    }

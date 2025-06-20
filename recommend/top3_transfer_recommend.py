#top3_transfer_recommned.py
from pathlib import Path
from joblib import load
import pandas as pd
from recommend.hybrid_scheduler import HybridScheduler
from utils.preprocess import parse_model1_input, parse_bed_status_counts

from utils.db_loader import get_latest_realtime_data

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
    """
    실시간 병상 정보 기반 자동 병동 추천
    - 공병상이 있는 병동 추천
    - 공병상 없어도 가중치 기반 추천
    - 최후 fallback: 비어 있는 병동이라도 추천
    """
    try:
        # 1. 실시간 병상 데이터 로딩
        realtime_json = get_latest_realtime_data()
        # 2. 병동 데이터 파싱
        bed_info = parse_model1_input(realtime_json)

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

        print("입력된 병동 목록:", df_live["ward"].unique())
        print("병상 수 요약:\n", df_live[["ward", "embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct", "total_beds"]])

        # 3. 모델 기반 추천 시도

        ranked = model.recommend(icd=icd_code, df_live=df_live, top_k=3)


        print(" >> 추천 후보군 (점수 있는 ward 수):", len(ranked))
        print(" >> 추천 점수 목록:", ranked)
        if ranked:
            print("모델 기반 추천 완료")
            return {
                "recommended_wards": [{"ward": w, "score": round(s, 5)} for w, s in ranked],
                "icd": icd_code
            }

        # 4. 모델 추천이 비었을 경우  fallback
        print("모델 추천 결과 없음 >> fallback 실행")
        fallback_df = df_live.sort_values("occupancy").head(3)
        fallback_result = [
            {"ward": row["ward"], "score": 0.0}
            for _, row in fallback_df.iterrows()
        ]

        return {
            "recommended_wards": fallback_result,
            "icd": icd_code,
            "fallback": True
        }

    except Exception as e:
        raise ValueError(f"자동 전실 추천 오류: {e}")

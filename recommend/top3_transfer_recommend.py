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

def auto_transfer_recommend() -> dict:
    """
    실시간 병상 정보 기반 자동 병동 추천
    """
    try:
        # 1. 실시간 데이터 로딩
        realtime_json = get_latest_realtime_data()
        icd_code = "I63"  # 진단 코드: 임시로 하드코딩

        # 2. 병동 데이터 파싱 (wardCd → ward 이름으로 매핑 포함됨)
        bed_info = parse_model1_input(realtime_json)

        if not bed_info:
            return {
                "recommended_wards": [],
                "message": "실시간 병상 데이터가 없습니다."
            }

        # 3. DataFrame 생성
        df_live = pd.DataFrame(bed_info)
        df_live["total_beds"] = (
        df_live["embdCct"] +
        df_live["dschCct"] +
        df_live["useSckbCnt"] +
        df_live["admsApntCct"] +
        df_live["chupCct"]
        )
        df_live = df_live.groupby("ward", as_index=False).sum(numeric_only=True)

        # auto_transfer_recommend 내부에 디버깅 코드 추가
        print("입력된 병동 목록:", df_live["ward"].unique())
        print("병상 수 요약:\n", df_live[["ward", "embdCct", "dschCct", "useSckbCnt", "admsApntCct", "chupCct", "total_beds"]])

        # 4. 추천 실행
        ranked = model.recommend(icd=icd_code, df_live=df_live, top_k=3)
        print("추천 결과 확인:", ranked)

        return {
            "recommended_wards": [
                {"ward": ward, "score": round(score, 5)} for ward, score in ranked
            ],
            "icd": icd_code
        }

    except Exception as e:
        raise ValueError(f"자동 전실 추천 오류: {e}")

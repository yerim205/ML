# # retrain/top3_transfer_retrain.py

# import os
# import sys
# import joblib
# import shutil
# import logging
# from pathlib import Path
# from datetime import datetime
# from dotenv import load_dotenv

# from utils.infer_feedback_from_api import infer_feedback_from_api
# from utils.db_loader import get_realtime_data_for_days_ago
# from recommend.hybrid_scheduler import EDGES_BY_ICD, RAW_PRIORITY_WEIGHTS, HybridScheduler

# # ─── 설정 로딩 ─────────────────────────────
# ROOT = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(ROOT))
# load_dotenv(dotenv_path=ROOT / ".env")

# MODEL_PATH = ROOT / "model" / "model1.pkl"
# ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
# MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# # ─── 유틸: 가중치 갱신 수식 ───────────────
# def apply_weight_update(current: float, new: float, alpha: float = 0.6) -> float:
#     return alpha * current + (1 - alpha) * new


# # ─── 유틸: 모델 로딩 또는 초기화 ──────────
# def load_or_init_scheduler() -> HybridScheduler:
#     if MODEL_PATH.exists():
#         logger.info("기존 모델 로딩 완료")
#         return joblib.load(MODEL_PATH)
#     else:
#         logger.info("새 HybridScheduler 인스턴스 생성")
#         return HybridScheduler(edges_by_icd=EDGES_BY_ICD, priority_weights=RAW_PRIORITY_WEIGHTS)


# # ─── 유틸: 모델 저장 및 백업 ──────────────
# def save_and_archive_model(scheduler: HybridScheduler):
#     joblib.dump(scheduler, MODEL_PATH)
#     ts = datetime.now().strftime('%Y%m%d%H%M%S')
#     archive_path = ARCHIVE_MODEL_DIR / f"top3_transfer_{ts}.pkl"
#     archive_path.parent.mkdir(parents=True, exist_ok=True)
#     shutil.copy(MODEL_PATH, archive_path)
#     logger.info(f"모델 저장 완료: {MODEL_PATH}")
#     logger.info(f"아카이브 저장 완료: {archive_path}")


# # ─── 메인 재학습 함수 ─────────────────────
# def model1_retrain(raw_api_data: list):
#     logger.info("Top3 Transfer 모델 재학습 시작")
#     scheduler = load_or_init_scheduler()

#     if not hasattr(scheduler, "update_feedback"):
#         raise AttributeError("HybridScheduler에 update_feedback 메서드가 정의되어 있지 않습니다.")

#     # ── 1. 실시간 피드백 처리 ──
#     feedbacks = []
#     for record in raw_api_data:
#         try:
#             feedbacks.extend(infer_feedback_from_api(record))
#         except Exception as e:
#             logger.warning(f"실시간 피드백 추론 실패: {e}")
#     scheduler.update_feedback(feedbacks)
#     logger.info(f"실시간 피드백 반영 완료 (records={len(feedbacks)})")

#     # ── 2. 과거 피드백 처리 ──
#     days = 3
#     historical_feedbacks = []
#     for i in range(days):
#         try:
#             for past in get_realtime_data_for_days_ago(n=i):
#                 historical_feedbacks.extend(infer_feedback_from_api(past))
#         except Exception as e:
#             logger.warning(f"{i}일 전 피드백 추론 실패: {e}")
#     scheduler.update_feedback(historical_feedbacks)
#     logger.info(f"과거 {days}일 피드백 반영 완료 (records={len(historical_feedbacks)})")

#     # ── 3. 저장 및 아카이브 ──
#     save_and_archive_model(scheduler)

#     return {"status": "updated", "count": len(feedbacks) + len(historical_feedbacks)}


# # ─── 단독 실행 테스트 ──────────────────────
# if __name__ == "__main__":
#     dummy_api_records = [{"dissCd": f"{i:02d}"} for i in range(1, 6)]
#     model1_retrain(dummy_api_records)

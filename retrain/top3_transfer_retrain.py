# # retrain/top3_transfer_retrain.py
# # 필히 수정 요함
# import os
# import sys
# import shutil
# from pathlib import Path
# from datetime import datetime

# import pandas as pd
# from sqlalchemy import create_engine, text
# from dotenv import load_dotenv

# # ─── 환경 설정 ─────────────────
# ROOT = Path(__file__).parent.parent
# load_dotenv(dotenv_path=ROOT / ".env")

# # 프로젝트 루트를 PYTHONPATH에 추가하여 top3_transfer 모듈 접근
# sys.path.insert(0, str(ROOT))

# DATABASE_URL      = os.getenv("DATABASE_URL")
# ARCHIVE_MODEL_DIR = Path(os.getenv("ARCHIVE_MODEL_DIR", "./data/archive/models"))
# engine            = create_engine(DATABASE_URL, future=True)

# # ─── 하이브리드 스케줄러 로드 ────
# from api.scheduler import run_transfer_retrain


# # ─── 모델 파일 경로 ─────────────
# MODEL_DIR  = ROOT / "model"
# MODEL_PATH = MODEL_DIR / "model1.pkl"  # top3_transfer
# MODEL_DIR.mkdir(exist_ok=True, parents=True)
# ARCHIVE_MODEL_DIR.mkdir(exist_ok=True, parents=True)


# def model1_retrain(data: dict) -> dict:
#     """
#     Top3_Transfer 피드백 API용 함수
#     data: {'records': [{'icd':..., 'ward':..., 'reward':...}, ...]}
#     """
#     # 신규 피드백 적용
#     recs = data.get('records', [])
#     run_transfer_retrain.scheduler.update_feedback(recs)
#     # 과거 로그 기반 추가 업데이트 (7일)
#     hist = run_transfer_retrain.fetch_transfer_feedback(days=7)
#     run_transfer_retrain.scheduler.update_feedback(hist)

#     # 피클 갱신
#     from joblib import dump
#     dump(run_transfer_retrain.scheduler, MODEL_PATH)
#     # 아카이브
#     ts = datetime.now().strftime('%Y%m%d%H%M%S')
#     ARCHIVE_MODEL_DIR.mkdir(exist_ok=True, parents=True)
#     shutil.copy(MODEL_PATH, ARCHIVE_MODEL_DIR / f"top3_transfer_{ts}.pkl")
#     return {'status':'updated', 'count': len(recs)+len(hist)}

# if __name__ == '__main__':
#     # 단독 실행 시 피드백 재적용
#     model1_retrain({'records': []})

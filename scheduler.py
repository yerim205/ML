import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 1) .env 로드
ROOT = Path(__file__).parent
load_dotenv(dotenv_path=ROOT / ".env")

# 2) 모델별 크론 스케줄 읽기 (기본값 설정)
CRON_CONG = os.getenv("RETRAIN_CRON_CONG", "0 2 * * *")  # 예 - 매일 새벽 2시
# CRON_DIS = os.getenv("RETRAIN_CRON_DIS", "0 3 * * *")    # 예  - 매일 새벽 3시

# 크론 표현식 검증
def validate_cron(cron_expr, name):
    try:
        CronTrigger.from_crontab(cron_expr)
        return True
    except ValueError as e:
        logger.error(f" {name}: {cron_expr} - {e}")
        return False

# 3) 스케줄러 생성
sched = BlockingScheduler()

# 4) retrain 함수 등록
from icu_congestion.retrain.retrain import retrain_icu_congestion

# try:
#     from icu_discharge.retrain.retrain import retrain_icu_discharge
#     discharge_available = True
# except ImportError:
#     logger.warning("icu_discharge module not found. Skipping discharge retraining.")
#     discharge_available = False

# 안전한 실행 래퍼
def safe_retrain_wrapper(func, model_name):
    def wrapper():
        try:
            logger.info(f"재학습 중 {model_name}...")
            func()
            logger.info(f"{model_name} 재학습이 성공적으로 마무리 되었습니다. ")
        except Exception as e:
            logger.error(f"{model_name} 재학습 실패 : {str(e)}")
    return wrapper

# 스케줄 등록
if validate_cron(CRON_CONG, "congestion"):
    sched.add_job(
        safe_retrain_wrapper(retrain_icu_congestion, "ICU Congestion"),
        trigger=CronTrigger.from_crontab(CRON_CONG),
        name="retrain_congestion"
    )

# if discharge_available and validate_cron(CRON_DIS, "discharge"):
#     sched.add_job(
#         safe_retrain_wrapper(retrain_icu_discharge, "ICU Discharge"),
#         trigger=CronTrigger.from_crontab(CRON_DIS),
#         name="retrain_discharge"
#     )

logger.info(f"스케줄러가 시작되는 시간 :  {datetime.now(timezone.utc).isoformat()}")
logger.info(f"  - icu_congestion cron: {CRON_CONG}")
if discharge_available:
    logger.info(f"  - icu_discharge cron: {CRON_DIS}")

# 5) 스케줄러 실행
try:
    sched.start()
except (KeyboardInterrupt, SystemExit):
    logger.info("스케줄러가 멈춤.")

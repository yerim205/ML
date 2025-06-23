"""
scheduler.py

- ICU Congestion: 하루에 한번
- ICU Discharge: 하루에 한번
- Top3 Transfer: 하루에 한번

Run  `python scheduler.py`
"""
# scheduler.py
import logging
import multiprocessing
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from retrain.top3_transfer_retrain import model1_retrain
from retrain.icu_congestion_retrain import model2_retrain
from retrain.icu_discharge_retrain import model3_retrain

# ─── 로깅 설정 ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('scheduler')

# ─── 스케줄러 정의 ─────────────────────────
scheduler = BlockingScheduler()

# ─── 서브 프로세스로 실행할 함수 ────────────
def run_in_process(target_func, *args, **kwargs):
    p = multiprocessing.Process(target=target_func, args=args, kwargs=kwargs)
    p.start()
    return p

# ─── Top3 Transfer 재학습 (모델1) ─────────────
def transfer_polling_job():
    # 빈 피드백이라도 polling할 때마다 retrain 함수 호출
    model1_retrain({'records': []})

scheduler.add_job(
    func=lambda: run_in_process(transfer_polling_job),
    trigger=IntervalTrigger(minutes=1),
    id='top3_transfer_polling',
    name='Top3 Transfer - 데이터 변화 감지 polling (1분 간격)',
    replace_existing=True
)

# ─── ICU Congestion 재학습 (모델2) ───────────
scheduler.add_job(
    func=lambda: run_in_process(model2_retrain),
    trigger=CronTrigger(hour=0, minute=0),
    id='icu_congestion_daily',
    name='ICU Congestion - 매일 00:00 재학습',
    replace_existing=True
)

# ─── ICU Discharge 재학습 (모델3) ─────────────
scheduler.add_job(
    func=lambda: run_in_process(model3_retrain),
    trigger=CronTrigger(hour=0, minute=0),
    id='icu_discharge_daily',
    name='ICU Discharge - 매일 00:00 재학습',
    replace_existing=True
)

# ─── 메인 진입점 ──────────────────────────────
if __name__ == '__main__':
    logger.info('스케줄러가 시작되었습니다.')
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('스케줄러가 종료되었습니다.')

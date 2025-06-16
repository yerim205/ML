"""
scheduler.py

- ICU Congestion: 하루에 한번
- ICU Discharge: 하루에 한번
- Top3 Transfer: 데이터의 변화가 감지되었을때

Run  `python scheduler.py`
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import multiprocessing

from retrain.icu_congestion_retrain import model2_retrain as retrain_congestion
from retrain.icu_discharge_retrain import model3_retrain as retrain_discharge

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('scheduler')

scheduler = BlockingScheduler()

def run_in_process(func, *args, **kwargs):
    p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
    p.start()
    return p

# 1. ICU Congestion retrain: 매일 재학습 시간 00:00
scheduler.add_job(
    func=lambda: run_in_process(retrain_congestion),
    trigger=CronTrigger(hour='0', minute='0'),
    id='icu_congestion_daily',
    name='ICU Congestion 매일 재학습 시간 00:00',
    replace_existing=True
)

# 2. ICU Discharge retrain: 매일 재학습 시간 00:00
scheduler.add_job(
    func=lambda: run_in_process(retrain_discharge),
    trigger=CronTrigger(hour='0', minute='0'),
    id='icu_discharge_daily',
    name='ICU Discharge 매일 재학습 시간 00:00',
    replace_existing=True
)

# 3. Top3 Transfer retrain: 데이터 변화 polling
def run_transfer_retrain():
    from retrain.top3_transfer_retrain import model1_retrain
    model1_retrain({'records': []})

scheduler.add_job(
    func=lambda: run_in_process(run_transfer_retrain),
    trigger=IntervalTrigger(minutes=1),
    id='top3_transfer_polling',
    name='Top3 Transfer retrain polling every minute',
    replace_existing=True
)

if __name__ == '__main__':
    logger.info('스케줄러가 시작...')
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('스케줄러 멈춤.')

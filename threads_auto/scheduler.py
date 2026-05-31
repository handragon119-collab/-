"""APScheduler로 정해진 시간에 자동 게시를 반복 실행합니다."""

import random
import time
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from threads_auto.runner import run_once


def _job() -> None:
    # 안전장치 ③: 예정 시각에 0~N분 랜덤 지연을 더해 봇 패턴을 피합니다.
    if config.SCHEDULE_JITTER_MINUTES > 0:
        jitter = random.randint(0, config.SCHEDULE_JITTER_MINUTES * 60)
        print(f"⏳ 봇 패턴 회피용 랜덤 지연: {jitter // 60}분 {jitter % 60}초")
        time.sleep(jitter)
    try:
        run_once()
    except Exception as exc:  # 스케줄러가 죽지 않도록 예외를 잡아서 로그만 남깁니다.
        print(f"[스케줄 작업 오류] {exc}")


def start() -> None:
    """SCHEDULE_CRON 설정에 따라 스케줄러를 시작합니다 (Ctrl+C로 종료)."""
    trigger = CronTrigger.from_crontab(config.SCHEDULE_CRON, timezone=config.TIMEZONE)
    scheduler = BlockingScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(_job, trigger, id="threads_auto_post")

    print(f"스케줄러 시작: cron='{config.SCHEDULE_CRON}' tz={config.TIMEZONE}")
    if config.SCHEDULE_JITTER_MINUTES > 0:
        print(f"실행 시각마다 0~{config.SCHEDULE_JITTER_MINUTES}분 랜덤 지연이 추가됩니다.")
    next_run = trigger.get_next_fire_time(None, datetime.now(scheduler.timezone))
    print("다음 실행 예정 시각:", next_run)
    print("종료하려면 Ctrl+C 를 누르세요.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n스케줄러를 종료합니다.")

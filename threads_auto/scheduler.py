"""APScheduler로 정해진 시간에 자동 게시를 반복 실행합니다."""

from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from threads_auto.runner import run_once


def _job() -> None:
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
    next_run = trigger.get_next_fire_time(None, datetime.now(scheduler.timezone))
    print("다음 실행 예정 시각:", next_run)
    print("종료하려면 Ctrl+C 를 누르세요.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n스케줄러를 종료합니다.")

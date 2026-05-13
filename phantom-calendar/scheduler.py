"""Scheduler — triggers the nightly sync pipeline at 21:00 local time."""

import threading
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sync_job import run_nightly_sync


def start_scheduler(timezone_str: str, trigger_time: str = "21:00") -> BackgroundScheduler:
    """Start and return a BackgroundScheduler with a configurable daily cron trigger.

    Args:
        timezone_str: Timezone name (e.g. 'America/New_York') for the cron trigger.
        trigger_time: HH:MM string for the daily trigger time (default '21:00').

    Returns:
        The started BackgroundScheduler instance.
    """
    try:
        hh, mm = map(int, trigger_time.split(":"))
    except (ValueError, AttributeError):
        hh, mm = 21, 0  # fallback to default

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_nightly_sync,
        trigger=CronTrigger(hour=hh, minute=mm, timezone=timezone_str),
        id="nightly_sync",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


def check_and_run_missed_sync(timezone_str: str) -> None:
    """Run a missed sync immediately if the current local time is 21:00 or later.

    Runs in a daemon thread so it doesn't block the app startup.
    """
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    if now.hour >= 21:
        thread = threading.Thread(target=run_nightly_sync, daemon=True)
        thread.start()

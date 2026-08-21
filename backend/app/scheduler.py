import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import record_scrape_run, table_is_empty
from app.sources.congress_trades import refresh_all_congress_trades
from app.sources.edgar_13f import refresh_13f
from app.sources.edgar_form4 import refresh_form4

logger = logging.getLogger("stocks.scheduler")

DAILY_LOOKBACK_DAYS = 7


def _run_refresh(name: str, fn, **kwargs) -> None:
    try:
        inserted, errors = fn(**kwargs)
        logger.info("refreshed %s: %d rows inserted, %d failures", name, inserted, errors)
        record_scrape_run(name, inserted, errors)
    except Exception:
        logger.exception("refresh failed for %s", name)
        record_scrape_run(name, 0, -1)  # -1 signals a total run failure, not just per-filing errors


def backfill_if_empty() -> None:
    """Runs once on startup so the dashboard has data immediately, instead of
    waiting for the next scheduled run, on a fresh/empty database."""
    if table_is_empty("insider_transactions"):
        _run_refresh("insiders", refresh_form4, count=100)
    if table_is_empty("institutional_holdings"):
        _run_refresh("institutions", refresh_13f, count=50)
    if table_is_empty("congress_trades"):
        _run_refresh("congress", refresh_all_congress_trades, year=date.today().year)


def run_daily_refresh() -> None:
    since = (date.today() - timedelta(days=DAILY_LOOKBACK_DAYS)).isoformat()
    _run_refresh("insiders", refresh_form4, count=200)
    _run_refresh("institutions", refresh_13f, count=100)
    _run_refresh("congress", refresh_all_congress_trades, year=date.today().year, since_date=since)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_refresh,
        CronTrigger(hour=9, minute=0),
        id="daily_refresh",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started: daily refresh registered for 09:00")
    return scheduler

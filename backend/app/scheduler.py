import logging
import time
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import record_scrape_run, table_is_empty
from app.sources.congress_trades import refresh_all_congress_trades
from app.sources.edgar_13f import refresh_13f
from app.sources.edgar_form4 import refresh_form4
from app.trading_engine import run_bot_once

logger = logging.getLogger("stocks.scheduler")

DAILY_LOOKBACK_DAYS = 7

# One failed 9am run used to mean a full day of staleness with no recovery
# attempt — a transient network blip against SEC/House Clerk/FMP shouldn't cost
# that much. Two retries with a short backoff before giving up and recording a
# real failure. Module-level (not a function default) so tests can shrink it.
RETRY_BACKOFFS_SECONDS = [30, 120]


def _run_refresh(name: str, fn, **kwargs) -> None:
    attempts = len(RETRY_BACKOFFS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            inserted, errors = fn(**kwargs)
            logger.info("refreshed %s: %d rows inserted, %d failures", name, inserted, errors)
            record_scrape_run(name, inserted, errors)
            return
        except Exception:
            if attempt < len(RETRY_BACKOFFS_SECONDS):
                backoff = RETRY_BACKOFFS_SECONDS[attempt]
                logger.warning(
                    "refresh failed for %s (attempt %d/%d), retrying in %ds",
                    name, attempt + 1, attempts, backoff, exc_info=True,
                )
                time.sleep(backoff)
            else:
                logger.exception("refresh failed for %s after %d attempts", name, attempts)
                record_scrape_run(name, 0, -1)  # -1 signals a total run failure, not just per-filing errors


def backfill_if_empty() -> None:
    """Runs once on startup so the dashboard has data immediately, instead of
    waiting for the next scheduled run, on a fresh/empty database. The bot is
    deliberately NOT included here, even though its tables start empty too —
    it defaults to disabled (bot_config.enabled=0) and must never place a
    trade before the user has reviewed the dashboard and turned it on."""
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


def run_bot_check() -> None:
    _run_refresh("bot", run_bot_once)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_refresh,
        CronTrigger(hour=9, minute=0),
        id="daily_refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        run_bot_check,
        # 30 minutes after the daily refresh, so the day's Product 2 inputs
        # (risk profile, latest snapshot) are settled before the bot decides
        # anything. run_bot_once() itself is a no-op unless bot_config.enabled.
        CronTrigger(hour=9, minute=30),
        id="bot_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started: daily refresh at 09:00, bot check at 09:30")
    return scheduler

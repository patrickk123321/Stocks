import logging
import time
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.alerts import check_and_notify
from app.db import record_scrape_run, table_is_empty
from app.sources.congress_trades import refresh_all_congress_trades
from app.sources.edgar_13f import refresh_13f
from app.sources.edgar_form4 import refresh_form4

logger = logging.getLogger("stocks.scheduler")

# US/Canadian Eastern Time — both follow the same UTC offset and DST rules, so
# one zone covers either reading of "9am/9pm Eastern". CronTrigger fields below
# are wall-clock Eastern hours; without this, APScheduler falls back to the
# host machine's local timezone, which on Railway is UTC — silently shifting
# "9:00am/9:00pm Eastern" to 9:00am/9:00pm UTC (4-5 hours early) instead.
EASTERN = ZoneInfo("America/New_York")

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
    waiting for the next scheduled run, on a fresh/empty database."""
    if table_is_empty("insider_transactions"):
        _run_refresh("insiders", refresh_form4, count=100)
    if table_is_empty("institutional_holdings"):
        _run_refresh("institutions", refresh_13f, count=50)
    if table_is_empty("congress_trades"):
        _run_refresh("congress", refresh_all_congress_trades, year=date.today().year)


def run_insider_refresh() -> None:
    """Insider (Form 4) trades get their own twice-daily job (9:00am and
    9:00pm Eastern) — filings land throughout the trading day, so a single
    once-daily check misses same-day activity for longer than necessary.
    Institutions (13F, quarterly data) and congress stay on the once-daily job
    below, where twice-daily makes no practical difference."""
    _run_refresh("insiders", refresh_form4, count=200)


def run_daily_refresh() -> None:
    """Institutions (13F, quarterly data) — once-daily is plenty; unlike
    congress trades, there's no buy-alert feature riding on this one."""
    _run_refresh("institutions", refresh_13f, count=100)


def run_congress_refresh() -> None:
    """Congress trades get 3 checks/day (see start_scheduler for the times and
    why) instead of institutions' once-daily, specifically to cut watchlist-alert
    latency — filings trickle in during business hours with no documented fixed
    publish time, so more frequent checks catch same-day buys sooner. Every
    newly-inserted row is handed to alerts.check_and_notify right after this
    refresh, so alerting stays buy-event-driven rather than a separate job."""
    since = (date.today() - timedelta(days=DAILY_LOOKBACK_DAYS)).isoformat()
    new_rows: list[dict] = []
    _run_refresh(
        "congress", refresh_all_congress_trades,
        year=date.today().year, since_date=since, on_new_rows=new_rows.extend,
    )
    if new_rows:
        check_and_notify(new_rows)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=EASTERN)
    scheduler.add_job(
        run_insider_refresh,
        CronTrigger(hour=9, minute=0, timezone=EASTERN),
        id="insider_refresh_am",
        replace_existing=True,
    )
    scheduler.add_job(
        run_insider_refresh,
        # Evening check, well after market close, to catch same-day filings
        # without waiting until the next morning.
        CronTrigger(hour=21, minute=0, timezone=EASTERN),
        id="insider_refresh_pm",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_refresh,
        CronTrigger(hour=9, minute=0, timezone=EASTERN),
        id="daily_refresh",
        replace_existing=True,
    )
    # 11am / 3pm / 7pm Eastern: spread across and after standard federal
    # business hours (House Clerk / Senate offices run ~9am-6pm ET, Mon-Fri).
    # There's no documented exact "batch publish" time from either chamber —
    # the House's bulk ZIP is republished daily "as filings come in" — so this
    # isn't a scientifically-derived optimum, just a practical latency win over
    # the previous once-daily 9am check for catching same-day buys.
    for hour, job_id in ((11, "congress_refresh_1"), (15, "congress_refresh_2"), (19, "congress_refresh_3")):
        scheduler.add_job(
            run_congress_refresh,
            CronTrigger(hour=hour, minute=0, timezone=EASTERN),
            id=job_id,
            replace_existing=True,
        )
    scheduler.start()
    logger.info(
        "scheduler started (America/New_York): insider refresh at 09:00 and 21:00, "
        "institutions refresh at 09:00, congress refresh at 11:00/15:00/19:00"
    )
    return scheduler

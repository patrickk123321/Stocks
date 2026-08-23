"""Tests for the scheduler's retry/backoff — previously a single failed 9am run
meant a full day of staleness with no recovery attempt.
"""

from unittest.mock import patch

import pytest

from app import db, scheduler
from app.db import get_last_scrape_run


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture(autouse=True)
def _zero_backoff(monkeypatch):
    # Real backoffs (30s, 120s) would make this test suite glacial — the retry
    # *count* and *final-outcome* logic is what's under test, not real timing.
    monkeypatch.setattr(scheduler, "RETRY_BACKOFFS_SECONDS", [0, 0])


def test_run_refresh_records_success_on_first_try(temp_db):
    calls = []

    def fn():
        calls.append(1)
        return (5, 0)

    scheduler._run_refresh("insiders", fn)
    assert len(calls) == 1

    last = get_last_scrape_run("insiders")
    assert last["inserted"] == 5
    assert last["error_count"] == 0


def test_run_refresh_retries_and_eventually_succeeds(temp_db):
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("transient failure")
        return (7, 0)

    scheduler._run_refresh("institutions", fn)
    assert len(calls) == 3  # failed twice, succeeded on the 3rd (final) attempt

    last = get_last_scrape_run("institutions")
    assert last["inserted"] == 7
    assert last["error_count"] == 0


def test_run_refresh_records_final_failure_after_exhausting_retries(temp_db):
    calls = []

    def fn():
        calls.append(1)
        raise RuntimeError("permanently broken")

    scheduler._run_refresh("congress", fn)
    assert len(calls) == 3  # 1 initial attempt + 2 retries, matching RETRY_BACKOFFS_SECONDS

    last = get_last_scrape_run("congress")
    assert last["error_count"] == -1  # -1 signals a total run failure, not per-filing errors


def test_run_bot_check_records_to_scrape_runs_via_run_refresh(temp_db):
    # run_bot_check just wraps run_bot_once in the same _run_refresh machinery
    # already tested above — this only checks the wiring, not run_bot_once's
    # own logic (covered in test_bot_runner.py).
    with patch("app.scheduler.run_bot_once", return_value=(2, 0)):
        scheduler.run_bot_check()
    last = get_last_scrape_run("bot")
    assert last["inserted"] == 2
    assert last["error_count"] == 0

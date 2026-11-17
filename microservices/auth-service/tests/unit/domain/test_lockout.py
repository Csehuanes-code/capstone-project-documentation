from datetime import UTC, datetime, timedelta

import pytest

from auth_service.domain.errors import AccountLocked
from auth_service.domain.lockout import FailedLoginTracker


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, duration: timedelta) -> None:
        self.current += duration


def test_fifth_failure_within_60_seconds_locks_temporarily() -> None:
    clock = FakeClock()
    tracker = FailedLoginTracker(clock, block_duration=timedelta(minutes=5))
    for _ in range(4):
        assert tracker.record_failure() is False
    assert tracker.record_failure() is True
    with pytest.raises(AccountLocked):
        tracker.record_failure()


def test_failures_outside_window_do_not_accumulate() -> None:
    clock = FakeClock()
    tracker = FailedLoginTracker(clock, block_duration=timedelta(minutes=5))
    for _ in range(4):
        tracker.record_failure()
    clock.advance(timedelta(seconds=61))
    assert tracker.record_failure() is False


def test_lock_expires_after_configured_duration() -> None:
    clock = FakeClock()
    tracker = FailedLoginTracker(clock, block_duration=timedelta(minutes=5))
    for _ in range(5):
        tracker.record_failure()
    clock.advance(timedelta(minutes=5))
    assert tracker.blocked_until is None
    assert tracker.record_failure() is False


def test_success_clears_failure_history() -> None:
    clock = FakeClock()
    tracker = FailedLoginTracker(clock, block_duration=timedelta(minutes=5))
    for _ in range(4):
        tracker.record_failure()
    tracker.record_success()
    assert tracker.record_failure() is False

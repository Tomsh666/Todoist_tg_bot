from __future__ import annotations

from app.dedup import UpdateDeduplicator
from app.limits import SlidingWindowRateLimiter


def test_rate_limiter_allows_limit_then_rejects() -> None:
    now = [100.0]
    limiter = SlidingWindowRateLimiter(2, 60, clock=lambda: now[0])
    assert limiter.allow(1)
    assert limiter.allow(1)
    assert not limiter.allow(1)
    assert limiter.allow(2)
    now[0] = 161.0
    assert limiter.allow(1)


def test_dedup_is_scoped_to_chat_and_expires() -> None:
    now = [100.0]
    dedup = UpdateDeduplicator(ttl_seconds=10, clock=lambda: now[0])
    assert dedup.first_seen((1, 4))
    assert not dedup.first_seen((1, 4))
    assert dedup.first_seen((2, 4))
    now[0] = 111.0
    assert dedup.first_seen((1, 4))


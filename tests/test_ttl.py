"""TTL / expiry tests."""

from __future__ import annotations

import time

from src import Cache


def test_default_ttl_applies_to_new_puts():
    c = Cache(max_items=10, default_ttl_seconds=0.1)
    c.put("a", 1)
    assert c.get("a") == 1
    time.sleep(0.2)
    assert c.get("a") is None


def test_per_key_ttl_overrides_default():
    c = Cache(max_items=10, default_ttl_seconds=10.0)
    c.put("short", "x", ttl_seconds=0.1)
    time.sleep(0.2)
    assert c.get("short") is None


def test_no_ttl_means_no_expiry():
    c = Cache(max_items=10)
    c.put("a", 1)
    time.sleep(0.05)
    assert c.get("a") == 1


def test_ttl_none_explicitly_disables_expiry():
    c = Cache(max_items=10, default_ttl_seconds=0.01)
    c.put("forever", 1, ttl_seconds=None)
    time.sleep(0.05)
    assert c.get("forever") == 1


def test_re_put_refreshes_ttl():
    c = Cache(max_items=10)
    c.put("a", 1, ttl_seconds=0.2)
    time.sleep(0.1)
    c.put("a", 2, ttl_seconds=0.2)  # should reset the clock
    time.sleep(0.15)
    # Only 0.15s have passed since the re-put; the key should still be alive.
    assert c.get("a") == 2


def test_expired_key_counts_as_miss_in_stats():
    c = Cache(max_items=10, default_ttl_seconds=0.05)
    c.put("a", 1)
    time.sleep(0.1)
    c.get("a")
    s = c.stats()
    assert s["misses"] == 1
    assert s["hits"] == 0

"""Tests for the ``max_memory_bytes`` eviction bound."""

from __future__ import annotations

import sys

from src import Cache


def _size(value: object) -> int:
    return sys.getsizeof(value)


def test_memory_bytes_tracks_total_value_size():
    c = Cache(max_items=10, max_memory_bytes=10_000)
    c.put("a", "hello")
    c.put("b", "world!")
    assert c.stats()["memory_bytes"] == _size("hello") + _size("world!")


def test_memory_bytes_eviction_drops_lru_when_bytes_exceeded():
    v1 = "a" * 1000
    v2 = "b" * 1000
    v3 = "c" * 1000
    # Budget fits two ~1KB strings but not three.
    budget = _size(v1) + _size(v2) + 10
    c = Cache(max_items=100, max_memory_bytes=budget)
    c.put("v1", v1)
    c.put("v2", v2)
    c.put("v3", v3)
    # v1 is least-recently-used and should have been evicted to make room.
    assert c.get("v1") is None
    assert c.get("v2") == v2
    assert c.get("v3") == v3
    assert c.stats()["evictions"] == 1


def test_memory_bytes_respects_recent_access():
    v1 = "a" * 1000
    v2 = "b" * 1000
    v3 = "c" * 1000
    budget = _size(v1) + _size(v2) + 10
    c = Cache(max_items=100, max_memory_bytes=budget)
    c.put("v1", v1)
    c.put("v2", v2)
    # Touching v1 makes v2 the LRU entry.
    assert c.get("v1") == v1
    c.put("v3", v3)
    assert c.get("v2") is None
    assert c.get("v1") == v1
    assert c.get("v3") == v3


def test_memory_bytes_updates_on_overwrite():
    small = "x"
    big = "x" * 5000
    c = Cache(max_items=10, max_memory_bytes=_size(big) + 100)
    c.put("k", small)
    before = c.stats()["memory_bytes"]
    c.put("k", big)
    after = c.stats()["memory_bytes"]
    assert before == _size(small)
    assert after == _size(big)


def test_memory_bytes_updates_on_delete_and_clear():
    c = Cache(max_items=10, max_memory_bytes=1_000_000)
    c.put("a", "hello")
    c.put("b", "world")
    assert c.stats()["memory_bytes"] > 0
    c.delete("a")
    assert c.stats()["memory_bytes"] == _size("world")
    c.clear()
    assert c.stats()["memory_bytes"] == 0


def test_memory_bytes_single_oversized_value_is_kept():
    # A value that on its own exceeds the budget should still be stored
    # (we can't evict the item we just inserted), but existing entries are
    # flushed to make room.
    c = Cache(max_items=10, max_memory_bytes=100)
    c.put("small", "x")
    oversized = "y" * 10_000
    c.put("big", oversized)
    assert c.get("big") == oversized
    # The small entry should have been evicted trying to satisfy the bound.
    assert c.get("small") is None


def test_max_memory_bytes_must_be_positive():
    import pytest

    with pytest.raises(ValueError):
        Cache(max_items=10, max_memory_bytes=0)
    with pytest.raises(ValueError):
        Cache(max_items=10, max_memory_bytes=-1)


def test_no_memory_bound_means_only_max_items_applies():
    c = Cache(max_items=3)
    for i in range(5):
        c.put(i, "x" * 10_000)
    assert len(c) == 3
    assert c.stats()["max_memory_bytes"] is None

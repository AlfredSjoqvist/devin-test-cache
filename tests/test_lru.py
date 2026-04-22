"""LRU behaviour tests."""

from __future__ import annotations

from src import Cache


def test_put_and_get_roundtrip(cache):
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_missing_key_returns_default(cache):
    assert cache.get("nope", default="fallback") == "fallback"


def test_missing_key_returns_none_by_default(cache):
    assert cache.get("nope") is None


def test_put_overwrites_existing_value(cache):
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_lru_eviction_order(cache):
    # Cache capacity is 4. Fill it, then access one, then insert a new key.
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    _ = cache.get("a")
    cache.put("e", 5)
    # 'b' was the least-recently-used, so it should be evicted.
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("e") == 5


def test_size_never_exceeds_max(big_cache):
    c = Cache(max_items=3)
    for i in range(10):
        c.put(i, i)
    assert len(c) <= 3


def test_delete_removes_item(cache):
    cache.put("a", 1)
    assert cache.delete("a") is True
    assert cache.get("a") is None


def test_delete_missing_returns_false(cache):
    assert cache.delete("never-there") is False


def test_clear_empties_cache(cache):
    cache.put("a", 1)
    cache.put("b", 2)
    cache.clear()
    assert len(cache) == 0


def test_clear_resets_stats(cache):
    cache.put("a", 1)
    cache.get("a")
    cache.get("missing")
    cache.clear()
    s = cache.stats()
    assert s["hits"] == 0
    assert s["misses"] == 0


def test_stats_tracks_hits_and_misses(cache):
    cache.put("a", 1)
    cache.get("a")
    cache.get("a")
    cache.get("missing")
    s = cache.stats()
    assert s["hits"] == 2
    assert s["misses"] == 1


def test_contains_operator(cache):
    cache.put("a", 1)
    assert "a" in cache
    assert "b" not in cache

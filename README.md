# devin-test-cache

A small in-memory cache library with LRU eviction and per-key TTL. Used by a
few internal services as a drop-in replacement for `functools.lru_cache` when
both bounded size and expiry are required.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e .
pip install -r requirements-dev.txt
```

## Use

```python
from devin_cache import Cache

c = Cache(max_items=1000, default_ttl_seconds=60)
c.put("k", "v")
c.put("k2", "v2", ttl_seconds=5)   # per-key TTL override
c.get("k")                         # -> "v"
c.get("missing", default=None)     # -> None
c.stats()                          # -> {"hits": ..., "misses": ..., "evictions": ..., "size": ...}
```

## Test

```bash
pytest
```

## Known issues

Users have reported sporadic stale reads under load and occasional exceptions
on cold-start. Reproduction is flaky but the failing cases are encoded in the
test suite (`pytest` currently has failures — see `tests/`).

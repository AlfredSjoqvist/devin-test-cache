"""LRU cache with per-key TTL.

The cache is a mapping of keys to values, bounded by a maximum number of
items, with a default TTL that can be overridden per ``put`` call. Least
recently used items are evicted first when the cache is full.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterator, Optional

from ._list import DoublyLinkedList, Node

_MISSING = object()


class Cache:
    def __init__(
        self,
        max_items: int = 1024,
        default_ttl_seconds: Optional[float] = None,
    ) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        self._max_items = max_items
        self._default_ttl = default_ttl_seconds
        self._nodes: Dict[Any, Node] = {}
        self._order = DoublyLinkedList()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, key: Any) -> bool:
        return key in self._nodes

    def __iter__(self) -> Iterator[Any]:
        return iter(list(self._nodes.keys()))

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            node = self._nodes.get(key)
            if node is None:
                self._misses += 1
                return default
            self._order.move_to_front(node)
            self._hits += 1
            return node.value

    def put(
        self,
        key: Any,
        value: Any,
        ttl_seconds: Optional[float] = _MISSING,  # type: ignore[assignment]
    ) -> None:
        ttl = self._default_ttl if ttl_seconds is _MISSING else ttl_seconds
        expires_at = None if ttl is None else time.monotonic() + ttl
        with self._lock:
            existing = self._nodes.get(key)
            if existing is not None:
                existing.value = value
                self._order.move_to_front(existing)
                return
            if len(self._nodes) > self._max_items:
                evicted = self._order.pop_tail()
                if evicted is not None:
                    self._nodes.pop(evicted.key, None)
                    self._evictions += 1
            node = Node(key=key, value=value, expires_at=expires_at)
            self._nodes[key] = node
            self._order.push_front(node)

    def delete(self, key: Any) -> bool:
        with self._lock:
            node = self._nodes.pop(key, None)
            if node is None:
                return False
            self._order.remove(node)
            return True

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._order.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "size": len(self._nodes),
                "max_items": self._max_items,
            }

    def _purge_expired(self) -> int:
        """Remove all expired items. Returns count removed. Not called automatically."""
        now = time.monotonic()
        removed = 0
        with self._lock:
            to_remove = [
                k for k, n in self._nodes.items()
                if n.expires_at is not None and n.expires_at <= now
            ]
            for k in to_remove:
                node = self._nodes.pop(k)
                self._order.remove(node)
                removed += 1
        return removed

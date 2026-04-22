"""LRU cache with per-key TTL and optional memory-bounded eviction.

The cache is a mapping of keys to values, bounded by a maximum number of
items and optionally by an approximate maximum memory footprint (measured
via :func:`sys.getsizeof` on stored values), with a default TTL that can be
overridden per ``put`` call. Least recently used items are evicted first
when the cache exceeds either bound.
"""

from __future__ import annotations

import sys
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
        max_memory_bytes: Optional[int] = None,
    ) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        if max_memory_bytes is not None and max_memory_bytes <= 0:
            raise ValueError("max_memory_bytes must be positive when set")
        self._max_items = max_items
        self._max_memory_bytes = max_memory_bytes
        self._default_ttl = default_ttl_seconds
        self._nodes: Dict[Any, Node] = {}
        self._order = DoublyLinkedList()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._memory_bytes = 0

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
            if node.expires_at is not None and node.expires_at <= time.monotonic():
                self._remove_node(node)
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
        value_size = sys.getsizeof(value)
        with self._lock:
            existing = self._nodes.get(key)
            if existing is not None:
                self._memory_bytes -= existing.size
                existing.value = value
                existing.size = value_size
                existing.expires_at = expires_at
                self._memory_bytes += value_size
                self._order.move_to_front(existing)
                self._enforce_bounds(protected=existing)
                return
            node = Node(key=key, value=value, expires_at=expires_at, size=value_size)
            self._nodes[key] = node
            self._order.push_front(node)
            self._memory_bytes += value_size
            self._enforce_bounds(protected=node)

    def delete(self, key: Any) -> bool:
        with self._lock:
            node = self._nodes.get(key)
            if node is None:
                return False
            self._remove_node(node)
            return True

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._order.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._memory_bytes = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "size": len(self._nodes),
                "max_items": self._max_items,
                "memory_bytes": self._memory_bytes,
                "max_memory_bytes": self._max_memory_bytes,
            }

    def _purge_expired(self) -> int:
        """Remove all expired items. Returns count removed."""
        now = time.monotonic()
        removed = 0
        with self._lock:
            to_remove = [
                n for n in self._nodes.values()
                if n.expires_at is not None and n.expires_at <= now
            ]
            for node in to_remove:
                self._remove_node(node)
                removed += 1
        return removed

    def _remove_node(self, node: Node) -> None:
        self._nodes.pop(node.key, None)
        self._order.remove(node)
        self._memory_bytes -= node.size

    def _enforce_bounds(self, protected: Optional[Node] = None) -> None:
        """Evict LRU entries until item and memory bounds are satisfied.

        ``protected`` is the node that was just inserted or updated; it will
        never be chosen as an eviction victim even if it alone exceeds
        ``max_memory_bytes``.
        """
        while len(self._nodes) > self._max_items or (
            self._max_memory_bytes is not None
            and self._memory_bytes > self._max_memory_bytes
        ):
            victim = self._order.peek_tail()
            if victim is None or victim is protected:
                return
            self._remove_node(victim)
            self._evictions += 1

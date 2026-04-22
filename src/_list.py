"""Doubly-linked list used by the cache to track LRU order in O(1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Node:
    key: Any
    value: Any
    expires_at: Optional[float]
    prev: Optional["Node"] = None
    next: Optional["Node"] = None


class DoublyLinkedList:
    def __init__(self) -> None:
        self._head: Optional[Node] = None
        self._tail: Optional[Node] = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def push_front(self, node: Node) -> None:
        node.prev = None
        node.next = self._head
        if self._head is not None:
            self._head.prev = node
        self._head = node
        if self._tail is None:
            self._tail = node
        self._size += 1

    def remove(self, node: Node) -> None:
        if node.prev is not None:
            node.prev.next = node.next
        else:
            self._head = node.next
        if node.next is not None:
            node.next.prev = node.prev
        else:
            self._tail = node.prev
        node.prev = None
        node.next = None
        self._size -= 1

    def move_to_front(self, node: Node) -> None:
        if node is self._head:
            return
        self.remove(node)
        self.push_front(node)

    def pop_tail(self) -> Optional[Node]:
        if self._tail is None:
            return None
        node = self._tail
        self.remove(node)
        return node

    def clear(self) -> None:
        self._head = None
        self._tail = None
        self._size = 0

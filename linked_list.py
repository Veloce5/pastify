"""
linked_list.py  (replaces doubly_linked_list.py + doubly_linked_list_quiz.py)

The two original files were identical in every way that mattered except the
shape of the payload each `Node` carried. A doubly linked list doesn't need
to know or care what's inside its nodes — so there's exactly one
implementation now, and callers just pass whatever tuple they need
(question/answer paths for Browse & Worksheet, or
(path, subject, correct_answer) for Quiz & Timed Test).
"""

from __future__ import annotations

import random
from typing import Any, Iterable


class Node:
    __slots__ = ("data", "next", "prev")

    def __init__(self, data: Any):
        self.data = data
        self.next: "Node | None" = None
        self.prev: "Node | None" = None


class DoublyLinkedList:
    def __init__(self):
        self.head: Node | None = None
        self.tail: Node | None = None

    def append(self, data: Any) -> Node:
        node = Node(data)
        if not self.head:
            self.head = self.tail = node
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        return node

    def extend(self, items: Iterable[Any]) -> None:
        for item in items:
            self.append(item)

    def get_all_nodes(self) -> list[Node]:
        nodes = []
        current = self.head
        while current:
            nodes.append(current)
            current = current.next
        return nodes

    def get_previous(self, node: Node | None) -> Node | None:
        return node.prev if node else None

    def get_next(self, node: Node | None) -> Node | None:
        return node.next if node else None

    def shuffle(self) -> None:
        nodes = self.get_all_nodes()
        random.shuffle(nodes)
        self.head = self.tail = None
        for node in nodes:
            self.append(node.data)

    def __len__(self) -> int:
        return len(self.get_all_nodes())

    def __bool__(self) -> bool:
        return self.head is not None

    @classmethod
    def from_iterable(cls, items: Iterable[Any]) -> "DoublyLinkedList":
        dll = cls()
        dll.extend(items)
        return dll

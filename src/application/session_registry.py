from __future__ import annotations

from threading import Lock
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class SessionRegistry(Generic[T]):
    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._items: dict[str, T] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> T:
        with self._lock:
            if session_id not in self._items:
                self._items[session_id] = self._factory()
            return self._items[session_id]

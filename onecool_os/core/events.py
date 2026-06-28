"""In-process event bus with SQLite-backed event logging."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A Core Engine event."""

    topic: str
    payload: dict[str, Any]


class EventBus:
    """Publishes events to subscribers and persists an audit log."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a handler to a topic."""

        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: dict[str, Any] | None = None) -> Event:
        """Publish an event and return it."""

        event = Event(topic=topic, payload=payload or {})
        encoded_payload = json.dumps(event.payload, sort_keys=True)
        with self._connection:
            self._connection.execute(
                "INSERT INTO event_log (topic, payload) VALUES (?, ?)",
                (event.topic, encoded_payload),
            )

        for handler in list(self._subscribers.get(topic, [])):
            handler(event)
        return event

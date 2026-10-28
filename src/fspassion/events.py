"""Flux d'événements vers l'interface (progression, messages, changements).

Chaque client (fenêtre de l'application, onglet du navigateur) a sa propre
file. Le serveur les envoie en « Server-Sent Events » (7.3).
"""

from __future__ import annotations

import queue
import threading
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: list[queue.Queue[dict[str, Any]]] = []

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, kind: str, **payload: Any) -> None:
        event = {"type": kind, **payload}
        with self._lock:
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(event)
            except queue.Full:
                # Client qui ne lit plus : on retire seulement son événement le plus
                # ancien, pour ne pas bloquer et ne pas perdre les plus récents.
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except (queue.Empty, queue.Full):
                    pass

    def toast(self, key: str, level: str = "info", **params: Any) -> None:
        """Message court traduit par l'interface (I7 : jamais de texte en dur)."""
        self.publish("toast", key=key, level=level, params=params)


bus = EventBus()

"""Tiny async event bus so modules stay decoupled."""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List

Handler = Callable[[Dict[str, Any]], Awaitable[None]]

log = logging.getLogger("sirgent.bus")


class Bus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Handler]] = {}

    def on(self, topic: str, handler: Handler) -> None:
        self._subs.setdefault(topic, []).append(handler)

    async def emit(self, topic: str, **data: Any) -> None:
        for h in self._subs.get(topic, []):
            try:
                await h(data)
            except Exception:  # noqa: BLE001
                log.exception("handler failed for %s", topic)


bus = Bus()

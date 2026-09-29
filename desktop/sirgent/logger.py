"""Logging + WebSocket broadcast bus for the SirGent desktop core.

Every log line is (a) written to a rotating file and (b) broadcast to the
web console via the shared WebSocket server so the console shows a live feed.
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Set

from .config import LOG_FILE

_ws_clients: Set[Any] = set()


def register_client(ws: Any) -> None:
    _ws_clients.add(ws)


def unregister_client(ws: Any) -> None:
    _ws_clients.discard(ws)


async def broadcast(payload: dict) -> None:
    if not _ws_clients:
        return
    msg = json.dumps(payload)
    dead = []
    for ws in list(_ws_clients):
        try:
            await ws.send(msg)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        unregister_client(ws)


def log_to_console(kind: str, msg: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop running (startup path): just append to file.
        _append_file(kind, msg)
        return
    loop.create_task(broadcast({"type": "log", "level": kind, "msg": msg}))
    _append_file(kind, msg)


def _append_file(kind: str, msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} [{kind}] {msg}"
    try:
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"sirgent.{name}")

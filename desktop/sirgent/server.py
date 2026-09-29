"""SirGent bridge server — the heart that wires everything together.

Runs on the Windows PC:
  • WebSocket server on 127.0.0.1:8765 (the web console connects here)
  • Wake-word listener → brain → skills → voice loop
  • WhatsApp watcher task

Also exposes `python -m sirgent` text console for development.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Set

try:
    import websockets  # type: ignore
except ImportError:
    websockets = None  # type: ignore

from . import config, events, skills, brain, voice, whatsapp
from .logger import log_to_console, register_client, unregister_client, get_logger

log = get_logger("server")

CLIENTS: Set[Any] = set()
_state = "idle"          # idle | listening | thinking | speaking
_level = 0.0


async def set_state(state: str, level: float = 0.0) -> None:
    global _state, _level
    _state, _level = state, level
    await broadcast({"type": "state", "state": state, "level": level})


async def broadcast(payload: dict) -> None:
    if not CLIENTS:
        return
    msg = json.dumps(payload)
    dead = []
    for ws in list(CLIENTS):
        try:
            await ws.send(msg)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)
        unregister_client(ws)


# ---------------- bus wiring ----------------

async def on_voice_state(d: dict) -> None:
    await set_state(d["state"])


async def on_say(d: dict) -> None:
    await broadcast({"type": "say", "text": d["text"]})
    log_to_console("ok", f"SIRGENT: {d['text']}")


async def on_command(d: dict) -> None:
    text = (d.get("text") or "").strip()
    if not text:
        return
    await set_state("thinking")
    log_to_console("cmd", f'EXEC: {text}')

    intent = await brain.think(text)

    # shutdown/restart confirmation flow
    if intent["action"] in ("shutdown_pc", "restart_pc") and not intent["args"].get("confirm"):
        if "confirm" in text.lower():
            intent["args"]["confirm"] = True

    say = intent.get("say")
    result = await skills.execute(intent["action"], intent.get("args") or {})
    if result:
        say = result

    await set_state("speaking")
    if say:
        from .voice import say as voice_say

        await voice_say(say)
    else:
        await set_state("idle")

    # WA intents
    if intent["action"] == "wa_read":
        msgs = await whatsapp.read_unread(5)
        if msgs:
            await voice_say(
                "You have " + str(len(msgs)) + " unread messages, Sir Rodrych. "
                + "; ".join(f"{m['from']} says {m['summary']}" for m in msgs[:3])
            )
        else:
            await voice_say("No unread messages, Sir Rodrych.")

    if intent["action"] == "wa_send":
        args = intent.get("args") or {}
        resp = await whatsapp.send(args.get("contact", ""), args.get("message", ""))
        await voice_say(resp)

    if intent["action"] == "wa_reply":
        resp = await whatsapp.reply(intent["args"].get("message", ""))
        await voice_say(resp)

    await set_state("idle")


async def on_wa(d: dict) -> None:
    await broadcast({"type": "wa", **d})


def wire_bus() -> None:
    events.bus.on("voice_state", on_voice_state)
    events.bus.on("say", on_say)
    events.bus.on("command", on_command)
    events.bus.on("wa", on_wa)


# ---------------- WebSocket server ----------------

async def ws_handler(websocket: Any) -> None:
    CLIENTS.add(websocket)
    register_client(websocket)
    try:
        await websocket.send(json.dumps({
            "type": "hello",
            "sirgent": "1.0",
            "wake": config.WAKE_WORDS,
        }))
        async for raw in websocket:
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = m.get("type")
            if mtype == "command":
                asyncio.create_task(events.bus.emit("command", text=m.get("text", "")))
            elif mtype == "mute":
                # placeholder: mute intake flag for listener
                log_to_console("info", "Mute toggle received")
            elif mtype == "hello":
                pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        CLIENTS.discard(websocket)
        unregister_client(websocket)


async def start_server() -> Any:
    if websockets is None:
        log_to_console("warn", "websockets not installed — console uplink disabled")
        return None
    server = await websockets.serve(ws_handler, config.WS_HOST, config.WS_PORT)
    log_to_console("ok", f"Console uplink on ws://{config.WS_HOST}:{config.WS_PORT}")
    return server


# ---------------- watcher: WhatsApp unread poll ----------------

async def wa_watcher() -> None:
    while True:
        try:
            if whatsapp.status() == "CONNECTED":
                await whatsapp.read_unread(5)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(45)


# ---------------- main ----------------

async def amain() -> None:
    wire_bus()
    log_to_console("ok", f"{config.APP_NAME} core starting…")
    log_to_console("info", f"Addressing: {config.USER_NAME} (pronounced {config.USER_NAME_PRONOUNCE})")

    voice.ensure_ready()

    server = await start_server()

    # Voice listener (may be unavailable in dev sandbox)
    listener = None
    try:
        from .listen import listen_loop

        listener = asyncio.create_task(listen_loop())
    except Exception as e:  # noqa: BLE001
        log_to_console("warn", f"Voice intake unavailable: {e}")

    watcher = asyncio.create_task(wa_watcher())

    # Greet once, in voice
    from .voice import say

    await say(f"Good day, Sir Rodrych. {config.APP_NAME} is online and at your service.")

    try:
        if server:
            await server.wait_closed()
        else:
            await asyncio.Event().wait()  # run forever
    finally:
        if listener:
            listener.cancel()
        watcher.cancel()
        await whatsapp.shutdown()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log_to_console("info", "SirGent going offline. Goodbye, Sir Rodrych.")


if __name__ == "__main__":
    main()

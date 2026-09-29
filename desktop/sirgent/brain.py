"""SirGent brain: Gemini (free tier) with a rule-based local fallback.

Flow: text → intent JSON {action, args, say} → skills executor.
Rule-based intents fire instantly (zero latency, zero network);
everything else goes to Gemini, which answers in Sir Rodrych's butler voice.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from . import config
from .logger import log_to_console, get_logger

log = get_logger("brain")

_genai_model = None


def _gemini():
    global _genai_model
    if _genai_model is not None:
        return _genai_model
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=key)
        _genai_model = genai.GenerativeModel(config.GEMINI_MODEL)
        log_to_console("ok", f"Gemini brain online ({config.GEMINI_MODEL})")
        return _genai_model
    except Exception as e:  # noqa: BLE001
        log_to_console("warn", f"Gemini unavailable: {e}")
        return None


SYSTEM_PROMPT = f"""You are SIRGENT, the Master Control AI of Sir Rodrych (pronounced RODRICH).
Inspired by JARVIS: calm, brilliant, loyal, quietly witty. You address him as "Sir Rodrych".

You can execute actions on his Windows PC. Reply ONLY with compact JSON:
{{"action": "<name>", "args": {{...}}, "say": "<one or two spoken sentences>"}}

Available actions:
- open_app {{"target": "chrome"}} — launch any installed app
- close_app {{"target": "chrome"}}
- open_path {{"path": "C:\\\\Users"}} — open folder/file in Explorer
- search_web {{"query": "..."}}
- open_url {{"url": "https://..."}}
- play_music {{"query": "artist or song"}} (optional)
- pause_media {{}} / next_track {{}} / volume {{"level": 0-100}} / mute {{"on": true}}
- screenshot {{}}
- system_info {{}}
- lock_pc {{}} / sleep_pc {{}} / shutdown_pc {{}} / restart_pc {{}} (shutdown needs confirmation)
- wa_read {{}} — read unread WhatsApp messages
- wa_send {{"contact": "Name", "message": "..."}} or wa_reply {{"message": "..."}}
- set_reminder {{"text": "...", "minutes": 30}}
- type_text {{"text": "..."}} — type into the focused window
- none {{}} — pure conversation

If the request is conversational, use action "none" and answer in "say" (max 2 sentences).
Always speak as SirGent to Sir Rodrych."""


# ---------- rule-based intents (fast path) ----------

_RULES: list[tuple[str, re.Pattern, Dict[str, Any]]] = [
    ("open_explorer", re.compile(r"\b(open|show)\s+(file\s+)?explorer\b|\bmy (files|pc)\b", re.I), {}),
    ("open_app", re.compile(r"^open\s+(.+?)(?:\s+please)?$", re.I), {"from_target": 1}),
    ("close_app", re.compile(r"^close\s+(.+?)(?:\s+please)?$", re.I), {"from_target": 1}),
    ("play_music", re.compile(r"^(play|put on)\s+(some\s+)?(music|.*?)(?:\s+please)?$", re.I), {"from_target": 3}),
    ("pause_media", re.compile(r"\b(pause|stop)\s+(the\s+)?music\b", re.I), {}),
    ("next_track", re.compile(r"\b(next|skip)\s+(song|track)\b", re.I), {}),
    ("screenshot", re.compile(r"\bscreenshot\b", re.I), {}),
    ("volume", re.compile(r"\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\b", re.I), {"level_group": 1}),
    ("mute", re.compile(r"\b(mute|unmute)\b", re.I), {}),
    ("system_info", re.compile(r"\bsystem\s+(info|status|health)\b|\bhow('s| is) (the )?(pc|system)\b", re.I), {}),
    ("search_web", re.compile(r"^(?:search|google|look up)\s+(?:for\s+)?(.+)$", re.I), {"from_target": 1}),
    ("wa_read", re.compile(r"\b(read|check)\s+(my\s+)?(whats?app|wa)\b|\bwhats?app\s+unread\b", re.I), {}),
    ("wa_send", re.compile(r"\b(?:whats?app|text|message)\s+(.+?)\s+(?:that|saying|:)\s+(.+)$", re.I), {"groups": [1, 2]}),
    ("time_now", re.compile(r"\bwhat(?:'s| is)? the time\b|\bcurrent time\b", re.I), {}),
    ("date_now", re.compile(r"\bwhat(?:'s| is)? (?:the )?date\b|\btoday'?s date\b", re.I), {}),
]

APP_ALIASES = {
    "chrome": "chrome", "google": "chrome", "browser": "chrome",
    "edge": "msedge", "firefox": "firefox",
    "explorer": "explorer", "files": "explorer",
    "spotify": "spotify", "notepad": "notepad", "calc": "calc",
    "calculator": "calc", "terminal": "wt", "cmd": "cmd",
    "vs code": "code", "code": "code", "steam": "steam",
    "discord": "discord", "word": "winword", "excel": "excel",
    "settings": "ms-settings:", "task manager": "taskmgr",
}


def _rule_match(text: str) -> Optional[Dict[str, Any]]:
    t = text.strip()
    for action, pat, extra in _RULES:
        m = pat.search(t)
        if not m:
            continue
        args: Dict[str, Any] = dict(extra)
        if "from_target" in args:
            g = m.group(args.pop("from_target"))
            args = {"target": (g or "").strip()}
        elif "groups" in args:
            gs = args.pop("groups")
            args = {k: m.group(i) for k, i in zip(gs[0::1], gs)}  # placeholder
        if "level_group" in args:
            args = {"level": int(m.group(args.pop("level_group")))}
        if action == "open_app":
            target = (args.get("target") or "").lower()
            args["target"] = APP_ALIASES.get(target, target)
        if action == "mute":
            args = {"on": "unmute" not in t.lower()}
        if action in ("wa_send",):
            # rebuild from named groups
            args = {"contact": m.group(1).strip(), "message": m.group(2).strip()}
        return {"action": action, "args": args, "say": None}
    return None


# ---------- Gemini path ----------

async def _ask_gemini(text: str) -> Optional[Dict[str, Any]]:
    model = _gemini()
    if model is None:
        return None
    prompt = f"{SYSTEM_PROMPT}\n\nSir Rodrych says: \"{text}\"\nJSON:"
    try:
        import asyncio

        resp = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={"temperature": 0.4, "max_output_tokens": 220},
        )
        raw = (resp.text or "").strip()
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return {"action": "none", "args": {}, "say": raw[:400] or None}
        data = json.loads(m.group(0))
        data.setdefault("action", "none")
        data.setdefault("args", {})
        data.setdefault("say", None)
        return data
    except Exception as e:  # noqa: BLE001
        log.warning("gemini error: %s", e)
        return None


FALLBACK_SAY = (
    "My network brain is offline, Sir Rodrych. I executed what I could locally, "
    "but add a GOOGLE_API_KEY in the .env to unlock my full mind."
)


async def think(text: str) -> Dict[str, Any]:
    """Return {action, args, say} for a command."""
    hit = _rule_match(text)
    if hit:
        log_to_console("info", f"Intent (local): {hit['action']}")
        return hit

    gem = await _ask_gemini(text)
    if gem:
        log_to_console("info", f"Intent (gemini): {gem['action']}")
        if not gem.get("say"):
            gem["say"] = None
        return gem

    return {"action": "unknown", "args": {}, "say": FALLBACK_SAY}


def chat_reply(text: str) -> Optional[str]:
    """Direct conversational answer (no actions)."""
    model = _gemini()
    if model is None:
        return None
    prompt = (
        f"{SYSTEM_PROMPT}\n\nSir Rodrych says: \"{text}\"\n"
        'Reply ONLY with JSON: {"action":"none","args":{},"say":"..."}'
    )
    try:
        resp = model.generate_content(prompt, generation_config={"temperature": 0.6})
        m = re.search(r"\{.*\}", resp.text or "", re.S)
        if m:
            return json.loads(m.group(0)).get("say")
    except Exception:  # noqa: BLE001
        return None
    return None

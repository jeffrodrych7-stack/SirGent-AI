"""WhatsApp power — automates WhatsApp Web with a persistent logged-in session.

First run: a Chrome window opens, Sir Rodrych scans the QR code once.
The session is stored in %LOCALAPPDATA%\\SirGent-AI\\wa_profile and reused
forever after. All actions run headless-ish (window minimized) so he can
keep working.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from . import config, events
from .logger import log_to_console, get_logger

log = get_logger("whatsapp")

_pw: Any = None
_browser: Any = None
_ctx: Any = None
_page: Any = None
_lock = asyncio.Lock()
_status = "DISCONNECTED"


def status() -> str:
    return _status


async def _ensure(max_wait: int = 90) -> Optional[Any]:
    """Launch/reuse the WhatsApp Web page. Returns page or None."""
    global _pw, _browser, _ctx, _page, _status
    async with _lock:
        if _page is not None:
            try:
                if await _page.title() is not None:
                    return _page
            except Exception:  # noqa: BLE001
                _page = None

        _status = "CONNECTING"
        await events.bus.emit("wa", event="status", status=_status)
        log_to_console("info", "Booting WhatsApp Web bridge…")

        def _launch():
            from playwright.async_api import async_playwright  # type: ignore

            return async_playwright()

        try:
            _pw = await _launch().start()
            _ctx = await _pw.chromium.launch_persistent_context(
                user_data_dir=str(config.WA_CHROME),
                headless=False,
                args=["--window-position=2000,2000", "--window-size=1,1"],
            )
            _page = _ctx.pages[0] if _ctx.pages else await _ctx.new_page()
            await _page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            # Wait for either the chat list (logged in) or QR (needs scan)
            logged_in = await _page.wait_for_selector(
                "[data-tab], div[role='grid']", timeout=max_wait * 1000
            )
            if not logged_in:
                _status = "QR PENDING"
                await events.bus.emit("wa", event="status", status=_status)
                log_to_console("warn", "Scan the QR in the opened window, Sir Rodrych.")
                await _page.wait_for_selector("[data-tab]", timeout=max_wait * 1000)

            _status = "CONNECTED"
            await events.bus.emit("wa", event="status", status=_status)
            log_to_console("ok", "WhatsApp bridge online — session saved")
            return _page
        except Exception as e:  # noqa: BLE001
            log.warning("whatsapp init failed: %s", e)
            _status = "ERROR"
            await events.bus.emit("wa", event="status", status=_status)
            log_to_console("warn", f"WhatsApp bridge failed: {e}")
            return None


async def read_unread(limit: int = 5) -> List[Dict[str, str]]:
    """Return up to `limit` unread chats: [{from, summary}]."""
    page = await _ensure()
    if page is None:
        return []
    try:
        chats = await page.evaluate(
            """
            (limit) => {
              const out = [];
              const rows = document.querySelectorAll("[data-tab] div[role='row'], div[aria-label='Chat list'] div[role='row']");
              let n = 0;
              for (const r of rows) {
                const unreadBadge = r.querySelector("[aria-label*='unread'], span[aria-label='" + (r.getAttribute('aria-label')||'').match(/\\d+/) + "']");
                const nameEl = r.querySelector("span[title]");
                const msgEl = r.querySelector("div[role='row'] span[title], span[title]:not([title=''])");
                if (nameEl && unreadBadge && n < limit) {
                  out.push({ from: nameEl.title, summary: (msgEl && msgEl.title) || "" });
                  n++;
                }
              }
              return out;
            }
            """,
            limit,
        )
        for c in chats:
            await events.bus.emit("wa", event="message", **c)
            log_to_console("wa", f"WA {c['from']} → {c['summary']}")
        return chats
    except Exception as e:  # noqa: BLE001
        log.warning("wa read failed: %s", e)
        return []


async def send(contact: str, message: str) -> str:
    """Send `message` to `contact` (fuzzy match on chat names)."""
    page = await _ensure()
    if page is None:
        return "WhatsApp isn't connected, Sir Rodrych."
    try:
        # Search
        search = page.locator("div[contenteditable='true'][data-tab='3']").first
        await search.click()
        await search.fill(contact)
        await page.wait_for_timeout(1800)
        # First result
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1200)
        # Message box
        box = page.locator("footer div[contenteditable='true']").last
        await box.click()
        await box.type(message, delay=18)
        await page.keyboard.press("Enter")
        log_to_console("wa", f"WA → {contact}: {message[:60]}")
        return f"Sent to {contact}, Sir Rodrych."
    except Exception as e:  # noqa: BLE001
        log.warning("wa send failed: %s", e)
        return f"Couldn't send to {contact} — {e}"


async def reply(message: str) -> str:
    """Reply in the currently open chat."""
    page = await _ensure()
    if page is None:
        return "WhatsApp isn't connected, Sir Rodrych."
    try:
        box = page.locator("footer div[contenteditable='true']").last
        await box.click()
        await box.type(message, delay=18)
        await page.keyboard.press("Enter")
        return "Reply sent, Sir Rodrych."
    except Exception as e:  # noqa: BLE001
        log.warning("wa reply failed: %s", e)
        return f"Reply failed: {e}"


async def shutdown() -> None:
    global _pw, _browser, _page
    try:
        if _ctx:
            await _ctx.close()
        if _pw:
            await _pw.stop()
    except Exception:  # noqa: BLE001
        pass
    _pw = _browser = _page = None

"""SirGent powers — everything SirGent can DO on the machine.

Local-first: every action has a Windows implementation via os/subprocess/
PowerShell (incl. media keys through keybd_event P/Invoke). Non-Windows
platforms get a graceful response so the hosted sandbox can smoke-test.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional

from . import config
from .logger import log_to_console, get_logger

log = get_logger("skills")

IS_WIN = sys.platform == "win32"

# Virtual-key codes for media/volume (keybd_event)
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

_KEYBD_PSTYPES = """
using System;
using System.Runtime.InteropServices;
public class SK {
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  public static void Tap(byte vk) {
    keybd_event(vk, 0, 0, UIntPtr.Zero);
    keybd_event(vk, 0, 2, UIntPtr.Zero); // KEYEVENTF_KEYUP
  }
}
"""


def _ps(script: str, timeout: int = 30) -> str:
    """Run a PowerShell snippet, return stdout."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        return (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        log.warning("powershell failed: %s", e)
        return ""


def _ps_once_setup() -> None:
    """Compile the keybd_event helper once per session."""
    if IS_WIN:
        _ps(f"Add-Type -TypeDefinition '{_KEYBD_PSTYPES}'", timeout=60)


def _tap_vk(vk: int, times: int = 1) -> None:
    if not IS_WIN:
        return
    taps = ";".join([f"[SK]::Tap({vk})"] * max(1, times))
    _ps(f"Add-Type -TypeDefinition '{_KEYBD_PSTYPES}'; {taps}")


def _elevate_ps(script: str, timeout: int = 60) -> None:
    """Run a PowerShell snippet elevated via UAC (Start-Process -Verb RunAs)."""
    inner = script.replace("'", "''")
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden "
         f"-ArgumentList '-NoProfile','-Command','{inner}'"],
        capture_output=True, timeout=timeout, check=False,
    )


# ---------------------------------------------------------------- apps / files

def open_app(target: str) -> str:
    t = (target or "").strip()
    if not t:
        return "Which app should I open, Sir Rodrych?"
    if IS_WIN:
        r = subprocess.run(
            ["cmd", "/c", "start", "", t],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if r.returncode == 0:
            return f"{t} launched."
        return f"I couldn't find {t}, Sir Rodrych."
    try:
        subprocess.Popen([t])
        return f"{t} launched (dev host)."
    except OSError:
        return f"I couldn't find {t} on this host, Sir Rodrych."


def close_app(target: str) -> str:
    if IS_WIN:
        _ps(f"Stop-Process -Name '{target}' -Force -ErrorAction SilentlyContinue")
        return f"Closed {target}, Sir Rodrych."
    return "Closing apps is a Windows power."


def open_path(path: str) -> str:
    p = Path(path or str(Path.home())).expanduser()
    if IS_WIN:
        os.startfile(str(p))  # type: ignore[attr-defined]  # noqa: S606
    else:
        webbrowser.open(f"file://{p}")
    return f"Opened {p}."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searching for {query}, Sir Rodrych."


def open_url(url: str) -> str:
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)
    return "Opening it now."


# ---------------------------------------------------------------- media

def play_music(query: str = "") -> str:
    ql = (query or "").lower().strip()
    music_dirs = [Path.home() / "Music", Path.home() / "Downloads"]
    exts = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
    track: Optional[Path] = None
    for d in music_dirs:
        if not d.exists():
            continue
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() in exts:
                if ql and ql not in f.stem.lower():
                    continue
                track = f
                break
        if track:
            break
    if track:
        if IS_WIN:
            os.startfile(str(track))  # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{track}")
        return f"Playing {track.stem}, Sir Rodrych."
    if ql:
        webbrowser.open(f"https://open.spotify.com/search/{ql}")
        return f"No local match — searching Spotify for {ql}."
    return "I found no music, Sir Rodrych."


def play_pause() -> str:
    _tap_vk(VK_MEDIA_PLAY_PAUSE)
    return "Toggled playback."


def next_track() -> str:
    _tap_vk(VK_MEDIA_NEXT)
    return "Next track."


def volume(level: Optional[int] = None, mute: Optional[bool] = None) -> str:
    if mute is not None:
        _tap_vk(VK_VOLUME_MUTE)
        return "Muted." if mute else "Sound restored."
    if level is not None:
        lvl = max(0, min(100, int(level)))
        # assume a mid baseline: tap down 50x then up lvl times for precision
        _tap_vk(VK_VOLUME_MUTE)          # ensure known state
        _tap_vk(VK_VOLUME_DOWN, 50)
        if lvl > 0:
            _tap_vk(VK_VOLUME_UP, lvl)   # 50 taps ≈ 100% ⇒ 1 tap = 2%
        return f"Volume at {lvl} percent."
    return "Volume unchanged."


def screenshot() -> str:
    out = config.ROOT / f"screenshot_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"
    if IS_WIN:
        _ps(
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
            "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
            "$g=[System.Drawing.Graphics]::FromImage($bmp);"
            "$g.CopyFromScreen(0,0,0,0,$bmp.Size);"
            f"$bmp.Save('{out}');"
            "$g.Dispose();$bmp.Dispose()"
        )
        return f"Screenshot saved to {out}."
    return "Screenshots are a Windows power."


# ---------------------------------------------------------------- power / system

def system_info() -> str:
    cpu = _ps("(Get-CimInstance Win32_Processor).LoadPercentage") if IS_WIN else "12"
    try:
        import psutil  # type: ignore

        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        b = f", battery {battery.percent:.0f} percent" if battery else ""
        return f"CPU {cpu or 'unknown'} percent, RAM {ram:.0f} percent{b}. All systems nominal, Sir Rodrych."
    except Exception:  # noqa: BLE001
        return f"CPU {cpu or 'unknown'} percent. All systems nominal, Sir Rodrych."


def lock_pc() -> str:
    if IS_WIN:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)  # noqa: S603,S607
        return "Locking up."
    return "Lock is Windows-only."


def sleep_pc() -> str:
    if IS_WIN:
        _ps("Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class P{[DllImport(\"powrprof.dll\")]public static extern int SetSuspendState(int a,int b,int c);}';[P]::SetSuspendState(0,0,0)")
        return "Going to sleep, Sir Rodrych."
    return "Sleep is Windows-only."


def shutdown_pc(confirm: bool = False) -> str:
    if not confirm:
        return "Are you certain, Sir Rodrych? Say: confirm shutdown."
    if IS_WIN:
        subprocess.Popen("shutdown /s /t 5", shell=True)  # noqa: S603,S607
        return "Shutting down in five seconds. Goodbye, Sir Rodrych."
    return "Shutdown is Windows-only."


def restart_pc(confirm: bool = False) -> str:
    if not confirm:
        return "Restart as well, Sir Rodrych? Say: confirm restart."
    if IS_WIN:
        subprocess.Popen("shutdown /r /t 5", shell=True)  # noqa: S603,S607
        return "Restarting in five seconds."
    return "Restart is Windows-only."


def type_text(text: str) -> str:
    if IS_WIN:
        safe = text.replace("'", "''")
        _ps(f"(New-Object -ComObject WScript.Shell).SendKeys('{safe}')")
        return "Typed."
    return "Typing is a Windows power."


def elevate(cmd: str) -> str:
    """Run a PowerShell command elevated (triggers UAC)."""
    if IS_WIN:
        _elevate_ps(cmd)
        return f"Elevated execution requested: {cmd}"
    return "Elevation requires Windows."


# ---------------------------------------------------------------- reminders

async def set_reminder(text: str, minutes: float) -> str:
    async def _fire() -> None:
        await asyncio.sleep(max(0.1, minutes) * 60)
        from .voice import say

        await say(f"Sir Rodrych, reminder: {text}")

    asyncio.create_task(_fire())
    return f"Reminder set for {minutes:g} minutes, Sir Rodrych: {text}."


# ---------------------------------------------------------------- dispatcher

async def execute(action: str, args: Dict[str, Any]) -> str:
    """Run a brain action; returns the spoken result string."""
    try:
        if action == "open_app":
            return open_app(str(args.get("target", "")))
        if action == "close_app":
            return close_app(str(args.get("target", "")))
        if action == "open_path":
            return open_path(str(args.get("path", "")))
        if action == "open_explorer":
            return open_path(str(Path.home()))
        if action == "search_web":
            return search_web(str(args.get("query", "")))
        if action == "open_url":
            return open_url(str(args.get("url", "")))
        if action == "play_music":
            return play_music(str(args.get("query", "") or ""))
        if action == "pause_media":
            return play_pause()
        if action == "next_track":
            return next_track()
        if action == "volume":
            lvl = args.get("level")
            if "on" in args:
                return volume(mute=bool(args["on"]))
            return volume(int(lvl) if lvl is not None else None)
        if action == "mute":
            return volume(mute=bool(args.get("on", True)))
        if action == "screenshot":
            return screenshot()
        if action == "system_info":
            return system_info()
        if action == "lock_pc":
            return lock_pc()
        if action == "sleep_pc":
            return sleep_pc()
        if action == "shutdown_pc":
            return shutdown_pc(confirm=bool(args.get("confirm")))
        if action == "restart_pc":
            return restart_pc(confirm=bool(args.get("confirm")))
        if action == "type_text":
            return type_text(str(args.get("text", "")))
        if action == "elevate":
            return elevate(str(args.get("cmd", "")))
        if action == "set_reminder":
            return await set_reminder(
                str(args.get("text", "reminder")), float(args.get("minutes", 5))
            )
        if action == "time_now":
            return f"It is {_dt.datetime.now():%I:%M %p}, Sir Rodrych."
        if action == "date_now":
            return f"Today is {_dt.datetime.now():%A, %B %d, %Y}."
        if action == "none":
            return ""
        return ""
    except Exception as e:  # noqa: BLE001
        log.exception("skill failed")
        return f"That power misfired: {e}"

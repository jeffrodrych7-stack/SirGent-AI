"""SirGent voice output.

Strategy (all free, all local):
1. Piper TTS (neural, natural) — voice auto-downloaded on first run.
   `en_US-lessac-high` is a deep, calm male US voice (closest free match to a
   Michael-B.-Jordan-style delivery).
2. Windows SAPI fallback (Microsoft David) via PowerShell — always available.

Say(text, blocking) → writes a WAV into config.AUDIO_DIR and plays it.
Mouth motion is implied: the web console animates while core state == "speaking".
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

from . import config, events
from .logger import log_to_console, get_logger

log = get_logger("voice")

_piper_available: bool | None = None
_piper_bin: str | None = None


def _state_sync(state: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(events.bus.emit("voice_state", state=state))


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log_to_console("info", f"Downloading voice model → {dest.name}")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)


def _find_piper() -> str | None:
    """Locate piper.exe (bundled path or pip-installed piper-tts)."""
    global _piper_available, _piper_bin
    if _piper_available is not None:
        return _piper_bin

    candidates = [
        config.PIPER_DIR / "piper.exe",
        config.PIPER_DIR / "piper" / "piper.exe",
        "piper",
        "piper.exe",
    ]
    for c in candidates:
        try:
            subprocess.run(
                [str(c), "--help" if "piper" in str(c) else "-h"],
                capture_output=True,
                timeout=10,
            )
            _piper_available, _piper_bin = True, str(c)
            return _piper_bin
        except (OSError, subprocess.TimeoutExpired):
            continue
    _piper_available, _piper_bin = False, None
    return None


def _voice_files() -> tuple[Path, Path]:
    v = config.PIPER_DIR / "en_US-lessac-high.onnx"
    c = config.PIPER_DIR / "en_US-lessac-high.onnx.json"
    return v, c


def _ensure_voice_model() -> bool:
    if sys.platform != "win32":
        return False
    v, c = _voice_files()
    try:
        if not v.exists():
            _download(config.PIPER_VOICE_URL, v)
        if not c.exists():
            _download(config.PIPER_VOICE_CONF_URL, c)
        return True
    except Exception as e:  # noqa: BLE001
        log_to_console("warn", f"Voice model download failed: {e}")
        return False


def _piper_say(text: str, out: Path) -> bool:
    binp = _find_piper()
    if not binp:
        return False
    v, _ = _voice_files()
    if not v.exists():
        return False
    try:
        subprocess.run(
            [binp, "-m", str(v), "-f", str(out)],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=60,
            check=True,
        )
        return out.exists() and out.stat().st_size > 44
    except (OSError, subprocess.SubprocessError):
        return False


def _sapi_say(text: str, out: Path) -> bool:
    if sys.platform != "win32":
        return False
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('Microsoft David Desktop')
$s.Rate = -1
$s.SetOutputToWaveFile('{str(out).replace(chr(92), '/')}')
$s.Speak('{text.replace("'", "''")}')
$s.Dispose()
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=90,
            check=True,
        )
        return out.exists() and out.stat().st_size > 44
    except (OSError, subprocess.SubprocessError):
        return False


def _play_wav(path: Path) -> None:
    if sys.platform == "win32":
        # winsound is stdlib on Windows — zero deps.
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    else:
        # Non-Windows dev fallback.
        try:
            subprocess.run(
                ["aplay", str(path)], capture_output=True, timeout=60, check=False
            )
        except OSError:
            pass


async def say(text: str, broadcast_text: bool = True) -> None:
    """Speak `text` aloud. Announces speaking state over the bus."""
    if not text.strip():
        return
    if broadcast_text:
        await events.bus.emit("say", text=text)

    _state_sync("speaking")
    out = config.AUDIO_DIR / "say.wav"
    try:
        await asyncio.to_thread(_say_sync, text, out)
    except Exception:  # noqa: BLE001
        log.exception("say failed")

    _state_sync("idle")


def _say_sync(text: str, out: Path) -> None:
    ok = _piper_say(text, out) or _sapi_say(text, out)
    if not ok:
        log_to_console("warn", "TTS engines unavailable — text-only response")
        return
    _play_wav(out)


def speak_now(text: str) -> None:
    """Blocking speak, for use before the event loop is fully live."""
    out = config.AUDIO_DIR / "say.wav"
    if _piper_say(text, out) or _sapi_say(text, out):
        _play_wav(out)


def ensure_ready() -> None:
    """Pre-warm Piper binaries + voice model at startup (non-fatal)."""
    _find_piper()
    if _piper_available:
        _ensure_voice_model()
        log_to_console("ok", "Voice engine: Piper (neural, local)")
    else:
        log_to_console("info", "Piper not found — using Windows SAPI voice")

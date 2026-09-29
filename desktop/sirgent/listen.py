"""SirGent ears: wake-word detection + command capture, fully offline.

Pipeline:
  mic → Vosk (small en-us) → detect "hey sergent / hey sirgent" →
  capture the following sentence → emit on the bus as `command`.

Silence timeout ends capture; a hard cap prevents runaway recordings.
"""
from __future__ import annotations

import asyncio
import json
import os
import queue as _q
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from . import config, events
from .logger import log_to_console, get_logger

log = get_logger("listen")

_model = None
_running = False


def _vosk_dir() -> Path:
    return config.ROOT / "vosk-model"


def _ensure_vosk_model() -> Path | None:
    d = _vosk_dir()
    if d.exists() and any(d.iterdir()):
        return d
    z = config.ROOT / "vosk-small.zip"
    try:
        log_to_console("info", "Downloading wake-word model (~40 MB, one-time)")
        urllib.request.urlretrieve(config.VOSK_MODEL_URL, z)
        with zipfile.ZipFile(z) as f:
            f.extractall(config.ROOT)
        # zip contains e.g. vosk-model-small-en-us-0.15/
        extracted = config.ROOT / "vosk-model-small-en-us-0.15"
        if extracted.exists():
            extracted.rename(d)
        z.unlink(missing_ok=True)
        log_to_console("ok", "Wake-word model ready")
        return d
    except Exception as e:  # noqa: BLE001
        log_to_console("warn", f"Vosk model download failed: {e}")
        return None


def _stt() -> tuple:
    """Return (vosk.Model, words) or raise."""
    global _model
    if _model is not None:
        return _model
    from vosk import Model, KaldiRecognizer  # type: ignore

    d = _ensure_vosk_model()
    if d is None:
        raise RuntimeError("vosk model unavailable")
    _model = (Model(str(d)), config.WAKE_WORDS)
    return _model


def _list_audio_devices():
    try:
        import sounddevice as sd  # type: ignore

        return sd.query_devices()
    except Exception:  # noqa: BLE001
        return None


def _mic_loopback() -> None:
    """If no mic is found, log a clear instruction."""
    devices = _list_audio_devices()
    if devices is None:
        log_to_console("warn", "sounddevice unavailable — voice intake disabled")
        return
    inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
    if not inputs:
        log_to_console("warn", "No microphone detected — plug one in and restart")


async def listen_loop() -> None:
    """The always-on ear. Runs until cancelled."""
    global _running
    try:
        import sounddevice as sd  # type: ignore
        from vosk import KaldiRecognizer  # type: ignore
    except ImportError as e:
        log_to_console("warn", f"Audio stack missing ({e}) — text console only")
        return

    model, wake = _stt()
    samplerate = config.SAMPLE_RATE
    q: _q.Queue = _q.Queue()

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        q.put(bytes(indata))

    _running = True
    rec = KaldiRecognizer(model, samplerate)
    rec.SetWords(False)
    log_to_console("ok", f"Ears live — wake words: {', '.join(wake)}")

    import numpy as np  # local import to avoid hard dep if unused

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        capturing = False
        silence_frames = 0
        max_frames = int(10_000_000 / 1000)  # ~10 s cap
        frames_this_capture = 0

        while _running:
            data = await asyncio.to_thread(q.get)
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "").strip()
                if text:
                    if capturing:
                        await _emit_command(text)
                        capturing = False
                        frames_this_capture = 0
                    elif any(w in text for w in wake):
                        await events.bus.emit("voice_state", state="listening")
                        log_to_console("info", f'Heard: "{text}" — listening…')
                        capturing = True
                        silence_frames = 0
                if capturing:
                    silence_frames += 1
                    frames_this_capture += 1
                    if silence_frames > 40 or frames_this_capture > max_frames:
                        # ~1.2 s of silence → treat as end of utterance
                        final = json.loads(rec.FinalResult()).get("text", "").strip()
                        if final:
                            await _emit_command(final)
                        capturing = False
                        silence_frames = 0
            else:
                # Partial results can end capture early on long silence
                pass

        rec = None


async def _emit_command(text: str) -> None:
    log_to_console("cmd", f'SIR RODRYCH: "{text}"')
    await events.bus.emit("command", text=text, source="voice")


def stop() -> None:
    global _running
    _running = False

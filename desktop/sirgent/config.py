"""SIRGENT-AI desktop configuration."""
import os
from pathlib import Path

APP_NAME = "SirGent-AI"
USER_NAME = "Sir Rodrych"          # how SirGent addresses you
USER_NAME_PRONOUNCE = "RODRICH"    # phonetic hint for TTS engines
WAKE_WORDS = ["hey sergent", "hey sirgent", "hey sergeant"]

BRAIN = "gemini"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Core root: %LOCALAPPDATA%\SirGent-AI on Windows
if os.name == "nt":
    ROOT = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
else:
    ROOT = Path.home() / f".{APP_NAME.lower()}"

ROOT.mkdir(parents=True, exist_ok=True)
STATE_FILE = ROOT / "state.json"
WA_PROFILE = ROOT / "wa_profile"          # persistent WhatsApp Web session
WA_CHROME = ROOT / "wa_chrome"            # persistent browser profile
AUDIO_DIR = ROOT / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
PIPER_DIR = ROOT / "piper"
LOG_FILE = ROOT / "sirgent.log"

# Voice — all free/local. Piper voice (Michael-B.-Jordan-ish deep male US English).
PIPER_VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "en/en_US/lessac/high/en_US-lessac-high.onnx"
)
PIPER_VOICE_CONF_URL = PIPER_VOICE_URL + ".json"
# If Piper is unavailable, we fall back to Windows SAPI (David/Zira).
SAPI_VOICE_HINTS = ["Microsoft David", "Microsoft Guy", "Microsoft Mark"]

WS_PORT = 8765
WS_HOST = "127.0.0.1"

SAMPLE_RATE = 16000
FRAME_MS = 30
VOSK_MODEL_URL = (
    "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
)

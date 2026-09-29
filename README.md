# SIRGENT-AI — Master Control for Sir Rodrych

> *"Good day, Sir Rodrych. SirGent is online and at your service."*

A **JARVIS-class personal AI** for Windows: a local Python core with admin powers,
an offline voice loop with **"Hey Sergent / Hey SirGent"** wake words, a
**Tron-style red Master Control face** (3D, lip-synced), a **live web console**,
and **WhatsApp control** — plus a free **Gemini** brain for everything else.

---

## What's inside

```
┌──────────────────────────── YOUR WINDOWS PC ───────────────────────────┐
│                                                                        │
│  desktop/sirgent/            Python core (local-first, free stack)     │
│  ├─ server.py                WS bridge (127.0.0.1:8765) + main loop    │
│  ├─ listen.py                Wake word "Hey Sergent/SirGent" (Vosk)    │
│  ├─ voice.py                 TTS: Piper neural → SAPI fallback         │
│  ├─ brain.py                 Rule intents + Gemini (free tier)         │
│  ├─ skills.py                ALL local powers (apps, media, power…)    │
│  └─ whatsapp.py              WhatsApp Web automation (Playwright)      │
│                                                                        │
│  Web console (this repo's Vite app)                                    │
│  ├─ Tron-red 3D Master Control face (three.js, audio-reactive mouth)   │
│  ├─ Live log stream / telemetry / WhatsApp panel                       │
│  └─ Command line — type anything, SirGent executes                     │
└────────────────────────────────────────────────────────────────────────┘
```

**Everything runs locally.** The only cloud call is Gemini (free tier) for
open conversation — every power, wake word, and voice works offline.

---

## Quick start (Windows)

1. **Download this repo** (Code → Download ZIP, or `git clone`).
2. **Double-click `desktop/setup.bat`** → click **Yes** on the UAC prompt.
   - Installs Python (if needed), all Python powers, the WhatsApp browser engine,
     and a **SIRGENT-AI desktop shortcut**.
3. **Add your free Gemini key** (one time):
   - Get it at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Paste it into the `.env` file in the repo root: `GOOGLE_API_KEY=...`
4. **Double-click the SIRGENT-AI desktop shortcut.**
   - First WhatsApp use: a browser window opens — scan the QR **once**. Saved forever.
   - Voice models download once (~45 MB), then everything is offline.
5. **Open the console:** [http://localhost:5173](http://localhost:5173) — the face wakes up.

Say **"Hey Sergent"** (or *"Hey SirGent"*) — then speak your command.

---

## Powers

| Domain | Examples |
|---|---|
| **Apps** | "Open Chrome" · "Close Spotify" · "Open Task Manager" |
| **Files** | "Open Explorer" · "Open my Downloads" |
| **Media** | "Play music" · "Play Bohemian Rhapsody" · "Next track" · "Volume 40" · "Mute" |
| **System** | "Screenshot" · "System status" · "What's the time" |
| **Power** (guarded) | "Lock the PC" · "Sleep" · "Shutdown" (needs *confirm*) |
| **Admin** | Elevated PowerShell runs (UAC) — `elevate` action |
| **WhatsApp** | "Read my WhatsApp" · "WhatsApp Kai that I'm on my way" |
| **Reminders** | "Remind me in 30 minutes to stretch" |
| **Mind** (Gemini) | Any question — answered in butler voice, calls you **Sir Rodrych** |

---

## The web console

| Mode | Meaning |
|---|---|
| `DESKTOP UPLINK` | Core is running on this PC — full powers live |
| `DEMO CORE` | Hosted preview — face, logs and flow simulate; install on Windows to go live |

- Face: wireframe Master Control head, pulsing core, orbiting rings,
  **audio-reactive mouth bars**, bloom, scanlines — Tron-red throughout.
- Bottom line: type any command ("open spotify", "volume 30", "read my whatsapp").
- Panels: CPU/RAM telemetry, powers list, WhatsApp status + unread count.

---

## Voice stack (100% free)

| Stage | Tech |
|---|---|
| Wake word | [Vosk](https://alphacephei.com/vosk) small en-us, local |
| Speech→Text | Vosk, same session |
| Text→Speech | [Piper](https://github.com/rhasspy/piper) `en_US-lessac-high` (deep male US) → Windows SAPI "David" fallback |
| Playback | `winsound` (stdlib) |

> Name pronunciation is handled in `desktop/sirgent/config.py`
> (`USER_NAME_PRONOUNCE = "RODRICH"`) and in the system prompt so SirGent
> always says **"Sir Rodrych"** (ROD-rich).

---

## Repo layout

```
desktop/
  setup.bat            one-click admin installer (self-elevates)
  start_sirgent.bat    daily launcher
  env.example          copy → .env, add GOOGLE_API_KEY
  requirements.txt     all-free Python deps
  run_dev_console.sh   sandbox compile-check
  sirgent/             the core (see diagram above)
src/                  web console (Vite + React + three.js)
```

---

## Safety notes

- Shutdown/restart always ask for confirmation first.
- Admin powers surface a normal **UAC prompt** — Windows stays in charge.
- WhatsApp runs in your own browser profile with your own session; nothing is sent to any server except messages you tell SirGent to send (via your own logged-in browser).

**Ready, Sir Rodrych.** ⬢

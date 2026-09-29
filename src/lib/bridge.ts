// Bridge between the web console and the desktop SirGent core.
// Falls back to a rich DEMO mode when no desktop app is connected
// (e.g. viewing the hosted preview).

export type ConnState = "offline" | "connecting" | "online" | "demo";
export type VoiceState = "idle" | "listening" | "thinking" | "speaking";

export interface LogEntry {
  id: number;
  t: string;
  kind: "info" | "ok" | "warn" | "cmd" | "wa";
  msg: string;
}

export interface BridgeSnapshot {
  conn: ConnState;
  voice: VoiceState;
  level: number; // 0..1 audio/voice energy
  logs: LogEntry[];
  wakeWords: string[];
  waStatus: string;
  waUnread: number;
  screenshot: string | null; // data URL
  muted: boolean;
}

type Listener = () => void;

const DEMO_LOGS: Array<[LogEntry["kind"], string]> = [
  ["info", "Optics online — display array nominal"],
  ["ok", "Wake-word engine armed: 'Hey Sergent' / 'Hey SirGent'"],
  ["info", "Voice synthesis ready — local pipeline, zero cloud"],
  ["cmd", "EXEC: explorer.exe :: C:\\Users\\Rodrych"],
  ["ok", "File Explorer launched for Sir Rodrych"],
  ["info", "Scanning local audio library... 1,284 tracks indexed"],
  ["cmd", "EXEC: music.shuffle(genre='all')"],
  ["ok", "Playback started — volume 65%"],
  ["wa", "WhatsApp bridge: session active — 3 unread"],
  ["wa", "WA message from 'Kai' → 'You good for tonight?'"],
  ["cmd", "EXEC: wa.reply('Kai', 'Affirmative.')"],
  ["ok", "Reply dispatched via WhatsApp Web"],
  ["info", "System telemetry: CPU 12% · RAM 41% · GPU 8%"],
  ["info", "No anomalies detected in last sweep"],
  ["ok", "Admin elevation verified — full powers granted"],
];

const now = () =>
  new Date().toLocaleTimeString("en-GB", { hour12: false });

class Bridge {
  private listeners = new Set<Listener>();
  private ws: WebSocket | null = null;
  private demoTimers: number[] = [];
  private nextId = 1;

  snap: BridgeSnapshot = {
    conn: "offline",
    voice: "idle",
    level: 0,
    logs: [],
    wakeWords: ["Hey Sergent", "Hey SirGent"],
    waStatus: "DISCONNECTED",
    waUnread: 0,
    screenshot: null,
    muted: false,
  };

  subscribe = (l: Listener) => {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  };

  private emit() {
    this.snap = { ...this.snap };
    this.listeners.forEach((l) => l());
  }

  private log(kind: LogEntry["kind"], msg: string) {
    this.snap.logs = [
      ...this.snap.logs.slice(-160),
      { id: this.nextId++, t: now(), kind, msg },
    ];
    this.emit();
  }

  private setVoice(v: VoiceState, level = 0) {
    this.snap.voice = v;
    this.snap.level = level;
    this.emit();
  }

  // ---------- LIVE connection ----------
  connect(url: string) {
    this.stopDemo();
    this.disconnect(true);
    this.snap.conn = "connecting";
    this.emit();
    try {
      const ws = new WebSocket(url);
      this.ws = ws;
      ws.onopen = () => {
        this.snap.conn = "online";
        this.emit();
        this.log("ok", `Uplink established → ${url}`);
        ws.send(JSON.stringify({ type: "hello" }));
      };
      ws.onmessage = (ev) => this.handleMessage(ev.data);
      ws.onerror = () => {
        this.log("warn", "Uplink error — entering demo mode");
        this.startDemo();
      };
      ws.onclose = () => {
        if (this.snap.conn === "online") this.log("warn", "Uplink closed");
        if (this.snap.conn !== "demo") {
          this.snap.conn = "offline";
          this.emit();
        }
        this.ws = null;
      };
    } catch {
      this.log("warn", "Uplink failed — entering demo mode");
      this.startDemo();
    }
  }

  private handleMessage(raw: unknown) {
    try {
      const m = JSON.parse(String(raw)) as Record<string, unknown>;
      switch (m.type) {
        case "hello":
          if (Array.isArray(m.wake)) this.snap.wakeWords = m.wake as string[];
          this.log("ok", `SIRGENT core v${m.sirgent ?? "?"} reporting`);
          break;
        case "state":
          this.setVoice(m.state as VoiceState, Number(m.level ?? 0));
          break;
        case "log":
          this.log((m.level as LogEntry["kind"]) ?? "info", String(m.msg));
          break;
        case "wa":
          this.snap.waStatus = "CONNECTED";
          if (m.event === "unread") this.snap.waUnread = Number(m.count ?? 0);
          if (m.event === "message") {
            this.snap.waUnread = Math.max(0, this.snap.waUnread - 1);
            this.log("wa", `WA ${m.from} → ${m.summary}`);
          }
          this.emit();
          break;
        case "screenshot":
          this.snap.screenshot = `data:image/png;base64,${m.data}`;
          this.emit();
          break;
        default:
          break;
      }
    } catch {
      /* ignore malformed frames */
    }
  }

  disconnect(silent = false) {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
    if (!silent) {
      this.snap.conn = "offline";
      this.emit();
      this.log("info", "Uplink released");
    }
  }

  send(text: string) {
    const t = text.trim();
    if (!t) return;
    this.log("cmd", `EXEC: ${t}`);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "command", text: t }));
    } else {
      this.demoExec(t);
    }
  }

  setMuted(muted: boolean) {
    this.snap.muted = muted;
    this.emit();
    if (this.ws && this.ws.readyState === WebSocket.OPEN)
      this.ws.send(JSON.stringify({ type: "mute", on: muted }));
    this.log("info", muted ? "Audio intake muted" : "Audio intake live");
  }

  // ---------- DEMO mode (hosted preview) ----------
  startDemo() {
    this.stopDemo();
    this.disconnect(true);
    this.snap.conn = "demo";
    this.snap.waStatus = "SIMULATED";
    this.snap.waUnread = 3;
    this.emit();
    if (this.snap.logs.length === 0) this.log("ok", "DEMO CORE initialized");
    this.log("warn", "No desktop core found — running simulation");

    let i = 0;
    const cycle = window.setInterval(() => {
      const [kind, msg] = DEMO_LOGS[i % DEMO_LOGS.length];
      this.log(kind, msg);
      i++;
      if (kind === "cmd") {
        this.setVoice("thinking");
        window.setTimeout(() => {
          this.setVoice("speaking");
          window.setTimeout(() => this.setVoice("idle"), 2600);
        }, 1200);
      } else if (kind === "wa") {
        this.snap.waUnread = Math.max(0, this.snap.waUnread - (i % 2));
        this.emit();
      }
    }, 4200);
    this.demoTimers.push(cycle);

    // idle voice shimmer
    const breath = window.setInterval(() => {
      if (this.snap.voice === "idle") {
        this.snap.level = 0.06 + Math.random() * 0.05;
        this.emit();
      }
    }, 500);
    this.demoTimers.push(breath);
  }

  private demoExec(text: string) {
    this.setVoice("thinking");
    const replies: Array<[LogEntry["kind"], string]> = [
      ["ok", `Acknowledged, Sir Rodrych — "${text}" queued (demo core)`],
      ["warn", "Desktop core offline — action will execute on your PC"],
      ["info", `Parsed intent: ${text.slice(0, 48)}`],
    ];
    window.setTimeout(() => {
      const [k, m] = replies[Math.floor(Math.random() * replies.length)];
      this.log(k, m);
      this.setVoice("speaking");
      window.setTimeout(() => this.setVoice("idle"), 2400);
    }, 900);
  }

  private stopDemo() {
    this.demoTimers.forEach((t) => window.clearInterval(t));
    this.demoTimers = [];
  }
}

export const bridge = new Bridge();

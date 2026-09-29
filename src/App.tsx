import { useEffect, useMemo, useRef, useState } from "react";
import { bridge } from "./lib/bridge";
import { useBridge } from "./lib/useBridge";
import Face from "./face/Face";

const WAKE = ["HEY SERGENT", "HEY SIRGENT"];

const POWERS = [
  ["FILE EXPLORER", "open, search, launch anything"],
  ["MEDIA", "play / shuffle local music & video"],
  ["APPS", "launch + close any installed program"],
  ["SYSTEM", "volume, brightness, screenshots, shutdown"],
  ["ADMIN", "elevated execution when granted"],
  ["WHATSAPP", "read + send via WhatsApp Web"],
  ["VOICE", "offline wake-word + speech loop"],
];

function Badge({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 font-grid text-[10px] font-bold tracking-[0.2em] ${
        ok
          ? "border-tron-red/70 text-tron-red shadow-glow-sm animate-pulse-glow"
          : "border-tron-dim text-tron-dim"
      }`}
    >
      <span className={`h-1.5 w-1.5 ${ok ? "bg-tron-red shadow-glow-sm" : "bg-tron-dim"}`} />
      {children}
    </span>
  );
}

function Telemetry() {
  const [stats, setStats] = useState({ cpu: 12, ram: 41, net: 3 });
  useEffect(() => {
    const id = window.setInterval(() => {
      setStats((s) => ({
        cpu: Math.min(96, Math.max(3, s.cpu + (Math.random() * 14 - 7))),
        ram: Math.min(88, Math.max(22, s.ram + (Math.random() * 6 - 3))),
        net: Math.min(80, Math.max(1, s.net + (Math.random() * 10 - 5))),
      }));
    }, 1600);
    return () => window.clearInterval(id);
  }, []);
  return (
    <div className="space-y-3 p-3">
      {([["CPU CORE", stats.cpu], ["MEMORY", stats.ram], ["UPLINK", stats.net]] as const).map(
        ([label, v]) => (
          <div key={label}>
            <div className="mb-1 flex justify-between font-mono text-[10px] tracking-widest text-tron-ice/70">
              <span>{label}</span>
              <span className="text-tron-red">{Math.round(v)}%</span>
            </div>
            <div className="h-1.5 border border-tron-line bg-black/50">
              <div
                className="h-full bg-tron-red shadow-glow-sm transition-all duration-700"
                style={{ width: `${v}%` }}
              />
            </div>
          </div>
        )
      )}
    </div>
  );
}

const logColor: Record<string, string> = {
  info: "text-tron-ice/70",
  ok: "text-emerald-400/90",
  warn: "text-amber-400/90",
  cmd: "text-tron-red",
  wa: "text-sky-400/90",
};

function Logs() {
  const { logs } = useBridge();
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight });
  }, [logs]);
  return (
    <div ref={box} className="h-full space-y-0.5 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed">
      {logs.map((l) => (
        <div key={l.id} className="flex gap-2">
          <span className="shrink-0 text-tron-dim">{l.t}</span>
          <span className={logColor[l.kind]}>{l.msg}</span>
        </div>
      ))}
    </div>
  );
}

function CommandLine() {
  const [text, setText] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    bridge.send(text);
    setText("");
  };
  return (
    <form onSubmit={submit} className="flex items-center gap-2 border-t border-tron-line bg-black/60 px-3 py-2">
      <span className="font-grid text-xs font-bold tracking-widest text-tron-red">SIRGENT&gt;</span>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder='Type a command — or just say "Hey Sergent…"'
        className="w-full bg-transparent font-mono text-sm text-tron-ice outline-none placeholder:text-tron-dim/60"
      />
      <button type="submit" className="btn-tron clip-corner !px-3 !py-1" disabled={!text.trim()}>
        EXEC
      </button>
    </form>
  );
}

function VoiceCaption() {
  const { voice, conn } = useBridge();
  const label = useMemo(() => {
    switch (voice) {
      case "listening":
        return 'LISTENING — SAY "HEY SERGENT"';
      case "thinking":
        return "PROCESSING";
      case "speaking":
        return "SPEAKING";
      default:
        return conn === "online" ? "STANDBY — AWAITING WAKE WORD" : "STANDBY — DEMO CORE";
    }
  }, [voice, conn]);
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-6 flex flex-col items-center gap-2">
      <div className="flex gap-2">
        {WAKE.map((w) => (
          <span key={w} className="border border-tron-line bg-black/70 px-2 py-0.5 font-mono text-[10px] tracking-widest text-tron-dim">
            “{w}”
          </span>
        ))}
      </div>
      <div
        className={`font-grid text-xs font-bold tracking-[0.45em] text-tron-red ${
          voice === "idle" ? "opacity-70" : "animate-pulse-glow"
        }`}
        style={{ textShadow: "0 0 12px rgba(255,42,42,.9)" }}
      >
        {label}
      </div>
    </div>
  );
}

function WhatsAppPanel() {
  const { waStatus, waUnread, conn } = useBridge();
  return (
    <div className="p-3 font-mono text-[11px]">
      <div className="mb-2 flex items-center justify-between">
        <Badge ok={waStatus !== "DISCONNECTED"}>WA {waStatus}</Badge>
        <span className="text-tron-dim">WEB AUTOMATION</span>
      </div>
      <div className="mb-3 flex items-baseline gap-2">
        <span className="font-grid text-3xl font-black text-tron-red" style={{ textShadow: "0 0 14px rgba(255,42,42,.7)" }}>
          {waUnread}
        </span>
        <span className="text-tron-ice/60">unread for Sir Rodrych</span>
      </div>
      <p className="text-tron-ice/50">
        {conn === "online"
          ? "Bridge live — dictation and replies routed through desktop core."
          : "Connect the desktop core on your PC to activate reading + replying."}
      </p>
    </div>
  );
}

export default function App() {
  const snap = useBridge();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const wsProto = location.protocol === "https:" ? "wss" : "ws";
    // Desktop core (if running locally) exposes this port. Otherwise → demo.
    bridge.connect(`${wsProto}://${location.hostname}:8765`);
    window.setTimeout(() => {
      if (bridge.snap.conn !== "online") bridge.startDemo();
    }, 2500);
  }, []);

  const online = snap.conn === "online";

  return (
    <div className="scanlines vignette grid-bg flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-tron-line bg-black/70 px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 rotate-45 items-center justify-center border border-tron-red shadow-glow-sm">
            <div className="h-2 w-2 bg-tron-red shadow-glow" />
          </div>
          <h1 className="font-grid text-sm font-black tracking-[0.35em] text-tron-red" style={{ textShadow: "0 0 10px rgba(255,42,42,.8)" }}>
            SIRGENT-AI
          </h1>
          <span className="hidden font-mono text-[10px] tracking-[0.3em] text-tron-dim md:inline">
            // MASTER CONTROL
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge ok={online}>
            {snap.conn === "demo" ? "DEMO CORE" : online ? "DESKTOP UPLINK" : snap.conn.toUpperCase()}
          </Badge>
          <Badge ok={snap.voice !== "idle"}>{snap.voice.toUpperCase()}</Badge>
          <button className="btn-tron clip-corner !px-2 !py-0.5 !text-[10px]" onClick={() => bridge.setMuted(!snap.muted)}>
            {snap.muted ? "UNMUTE" : "MUTE"}
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* Left column */}
        <aside className="hidden w-64 shrink-0 flex-col gap-3 overflow-y-auto border-r border-tron-line p-3 lg:flex">
          <section className="panel clip-corner">
            <div className="panel-title">System</div>
            <Telemetry />
          </section>
          <section className="panel clip-corner">
            <div className="panel-title">Powers</div>
            <ul className="space-y-2 p-3 font-mono text-[10px]">
              {POWERS.map(([name, desc]) => (
                <li key={name}>
                  <span className="font-grid text-[10px] font-bold tracking-widest text-tron-red">{name}</span>
                  <div className="text-tron-ice/50">{desc}</div>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        {/* Face stage */}
        <section className="relative min-h-[300px] flex-1 animate-flicker">
          <Face />
          <VoiceCaption />
        </section>

        {/* Right column */}
        <aside className="flex w-full shrink-0 flex-col gap-3 border-l border-tron-line p-3 lg:w-72">
          <section className="panel clip-corner">
            <div className="panel-title">WhatsApp</div>
            <WhatsAppPanel />
          </section>
          <section className="panel clip-corner min-h-[120px] flex-1 overflow-hidden">
            <div className="panel-title">Uplink</div>
            <div className="p-3 font-mono text-[10px] text-tron-ice/60">
              <div>WAKE · “Hey Sergent” / “Hey SirGent”</div>
              <div>CALLSIGN · Sir Rodrych (RODRICH)</div>
              <div>BRAIN · Gemini (free tier)</div>
              <div>VOICE · local offline pipeline</div>
              <div>HOST · {online ? "Windows desktop" : "hosted preview"}</div>
            </div>
          </section>
        </aside>
      </main>

      {/* Log + command line */}
      <footer className="h-44 shrink-0 border-t border-tron-line bg-black/60">
        <div className="h-[calc(100%-41px)] overflow-hidden">
          <Logs />
        </div>
        <CommandLine />
      </footer>
    </div>
  );
}

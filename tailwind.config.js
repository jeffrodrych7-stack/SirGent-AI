/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tron: {
          red: "#ff2a2a",
          redglow: "#ff5533",
          ember: "#ff7a45",
          dark: "#0a0206",
          panel: "#14060b",
          line: "#3d0f14",
          dim: "#8a2530",
          ice: "#ffd9d0",
        },
      },
      fontFamily: {
        grid: ['"Orbitron"', "sans-serif"],
        mono: ['"Share Tech Mono"', "Consolas", "monospace"],
      },
      boxShadow: {
        "glow-sm": "0 0 6px rgba(255,42,42,.55)",
        glow: "0 0 14px rgba(255,42,42,.45), 0 0 34px rgba(255,42,42,.18)",
        "glow-lg": "0 0 22px rgba(255,42,42,.6), 0 0 60px rgba(255,42,42,.25)",
        inset: "inset 0 0 18px rgba(255,42,42,.12)",
      },
      keyframes: {
        pulseGlow: {
          "0%,100%": { opacity: "0.85" },
          "50%": { opacity: "0.4" },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        flicker: {
          "0%,100%": { opacity: "1" },
          "92%": { opacity: "1" },
          "93%": { opacity: "0.4" },
          "94%": { opacity: "1" },
          "96%": { opacity: "0.7" },
          "97%": { opacity: "1" },
        },
      },
      animation: {
        "pulse-glow": "pulseGlow 2.4s ease-in-out infinite",
        scanline: "scanline 7s linear infinite",
        flicker: "flicker 6s linear infinite",
      },
    },
  },
  plugins: [],
};

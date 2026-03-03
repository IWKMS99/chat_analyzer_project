import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--color-ink)",
        mint: "var(--color-accent-soft)",
        ocean: "var(--color-accent-strong)",
        sand: "var(--bg-canvas)"
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'IBM Plex Sans'", "sans-serif"]
      },
      boxShadow: {
        soft: "var(--surface-shadow)",
      },
      borderRadius: {
        card: "var(--radius-card)",
      },
      transitionDuration: {
        fast: "var(--motion-fast)",
        base: "var(--motion-normal)",
      },
    }
  },
  plugins: []
};

export default config;

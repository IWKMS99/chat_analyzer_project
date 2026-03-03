export function HeroPanel() {
  return (
    <section className="rounded-3xl border border-white/40 bg-[linear-gradient(120deg,#ffffffcf,#f4f7ffcf)] p-5 shadow-lg backdrop-blur">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Web Utility Mode</p>
      <h1 className="mt-2 text-3xl font-heading text-ink">Telegram Chat Analyzer</h1>
      <p className="mt-2 max-w-3xl text-sm text-slate-700">
        Upload Telegram Desktop export `result.json`, wait for async analysis, then inspect charts and detailed tables.
      </p>
    </section>
  );
}

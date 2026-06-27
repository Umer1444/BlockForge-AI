"use client";

import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      {/* ── Header ──────────────────────────────── */}
      <header className="mc-panel-header flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="text-3xl">⛏️</div>
          <h1 className="font-pixel text-lg text-white tracking-wider">
            BLOCK<span className="mc-text-glow-green">FORGE</span> AI
          </h1>
        </div>
        <nav className="flex gap-4">
          <Link href="/dashboard">
            <button className="mc-btn mc-btn-diamond text-xs">
              🎮 Launch Studio
            </button>
          </Link>
        </nav>
      </header>

      {/* ── Hero ────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <div className="relative mb-8">
          <div className="text-7xl mb-4 mc-craft-pulse">🧊</div>
          <h2 className="font-pixel text-2xl text-white mb-4 tracking-wide leading-relaxed">
            AI-Powered Video
            <br />
            <span className="mc-text-glow-diamond">Watermark Removal</span>
          </h2>
          <p className="font-pixel text-xs text-[var(--text-secondary)] max-w-xl mx-auto leading-6">
            GPU-accelerated inpainting studio powered by SAM & LaMa.
            Remove watermarks, logos, and unwanted objects while
            preserving pristine video quality.
          </p>
        </div>

        <div className="flex gap-6 mt-8">
          <Link href="/dashboard">
            <button className="mc-btn mc-btn-grass text-sm px-8 py-4">
              ⚔️ START FORGING
            </button>
          </Link>
          <button className="mc-btn mc-btn-stone text-sm px-8 py-4">
            📖 DOCS
          </button>
        </div>

        {/* ── Feature Cards ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 max-w-5xl w-full">
          {[
            {
              icon: "🤖",
              title: "AI Segmentation",
              desc: "SAM-powered automatic mask generation. Click to select, AI does the rest.",
              glow: "mc-text-glow-diamond",
            },
            {
              icon: "🎨",
              title: "GPU Inpainting",
              desc: "LaMa deep inpainting at full resolution with temporal consistency.",
              glow: "mc-text-glow-green",
            },
            {
              icon: "✨",
              title: "Quality Preserve",
              desc: "Original FPS, bitrate, and resolution. Zero quality degradation.",
              glow: "mc-text-glow-gold",
            },
          ].map((card, i) => (
            <div
              key={i}
              className="mc-panel p-6 rounded text-left hover:border-[var(--mc-emerald)] transition-all duration-200"
            >
              <div className="text-4xl mb-4">{card.icon}</div>
              <h3 className={`font-pixel text-sm mb-3 ${card.glow}`}>
                {card.title}
              </h3>
              <p className="font-pixel text-[10px] text-[var(--text-secondary)] leading-5">
                {card.desc}
              </p>
            </div>
          ))}
        </div>

        {/* ── Pipeline Steps ── */}
        <div className="mt-20 max-w-4xl w-full">
          <h3 className="font-pixel text-sm mc-text-glow-green mb-8">
            ⛏ PROCESSING PIPELINE
          </h3>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "Upload",
              "→",
              "Extract",
              "→",
              "Mask",
              "→",
              "Inpaint",
              "→",
              "Smooth",
              "→",
              "Enhance",
              "→",
              "Export",
            ].map((step, i) =>
              step === "→" ? (
                <span
                  key={i}
                  className="font-pixel text-xs text-[var(--mc-emerald)] self-center"
                >
                  →
                </span>
              ) : (
                <div
                  key={i}
                  className="mc-slot px-4 py-3 text-center rounded"
                >
                  <span className="font-pixel text-[10px] text-[var(--text-primary)]">
                    {step}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────── */}
      <footer className="border-t border-[var(--border-pixel)] py-6 text-center">
        <p className="font-pixel text-[8px] text-[var(--text-muted)]">
          BLOCKFORGE AI v1.0.0 • GPU-ACCELERATED VIDEO PROCESSING •
          CRAFTED WITH ⛏️ AND PYTORCH
        </p>
      </footer>
    </main>
  );
}

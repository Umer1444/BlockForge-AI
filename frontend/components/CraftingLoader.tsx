"use client";

import React from "react";

export default function CraftingLoader() {
    return (
        <div className="flex flex-col items-center justify-center gap-6 p-8">
            {/* Crafting Grid */}
            <div className="relative">
                <div className="mc-inventory grid-cols-3 w-36 h-36">
                    {[...Array(9)].map((_, i) => (
                        <div
                            key={i}
                            className="mc-slot"
                            style={{
                                animation: `mc-craft-pulse 1.5s ease infinite`,
                                animationDelay: `${i * 0.15}s`,
                            }}
                        >
                            {[0, 2, 4, 6, 8].includes(i) && (
                                <span
                                    className="text-lg"
                                    style={{
                                        animation: `mc-craft-spin 3s linear infinite`,
                                        animationDelay: `${i * 0.2}s`,
                                    }}
                                >
                                    {["⛏️", "🔥", "💎", "⚡", "✨"][
                                        [0, 2, 4, 6, 8].indexOf(i)
                                    ]}
                                </span>
                            )}
                        </div>
                    ))}
                </div>

                {/* Particles */}
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    {[...Array(5)].map((_, i) => (
                        <span
                            key={i}
                            className="absolute text-xs"
                            style={{
                                left: `${(i - 2) * 15}px`,
                                animation: `mc-particles 1.5s ease infinite`,
                                animationDelay: `${i * 0.3}s`,
                            }}
                        >
                            ✦
                        </span>
                    ))}
                </div>
            </div>

            {/* Arrow */}
            <div className="flex items-center gap-4">
                <span className="font-pixel text-2xl mc-text-glow-green mc-craft-pulse">
                    →
                </span>
            </div>

            {/* Output slot */}
            <div className="mc-slot w-16 h-16 border-[var(--mc-emerald)]" style={{ boxShadow: 'var(--glow-green)' }}>
                <span className="text-2xl mc-craft-pulse">🎬</span>
            </div>

            {/* Text */}
            <div className="text-center">
                <p className="font-pixel text-xs mc-text-glow-gold mb-2">
                    FORGING VIDEO...
                </p>
                <p className="font-pixel text-[8px] text-[var(--text-muted)]">
                    GPU processing in progress
                </p>
            </div>
        </div>
    );
}

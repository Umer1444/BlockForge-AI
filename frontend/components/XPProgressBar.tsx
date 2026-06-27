"use client";

import React from "react";

interface XPProgressBarProps {
    progress: number; // 0–100
    label?: string;
    showPercentage?: boolean;
}

export default function XPProgressBar({
    progress,
    label,
    showPercentage = true,
}: XPProgressBarProps) {
    const clamped = Math.max(0, Math.min(100, progress));

    return (
        <div className="w-full">
            {/* Label row */}
            <div className="flex justify-between items-center mb-2">
                {label && (
                    <span className="font-pixel text-[9px] text-[var(--text-secondary)] truncate max-w-[70%]">
                        {label}
                    </span>
                )}
                {showPercentage && (
                    <span className="font-pixel text-[10px] mc-text-glow-green">
                        {Math.round(clamped)}%
                    </span>
                )}
            </div>

            {/* Bar */}
            <div className="mc-xp-bar rounded-sm">
                <div
                    className="mc-xp-fill mc-shine"
                    style={{ width: `${clamped}%` }}
                />
            </div>

            {/* XP level indicator */}
            <div className="flex justify-center mt-1">
                <div
                    className="font-pixel text-[8px] px-2 py-0.5 rounded-sm"
                    style={{
                        background: "rgba(127, 255, 0, 0.15)",
                        color: "#7FFF00",
                        textShadow: "0 0 6px #7FFF00",
                    }}
                >
                    LVL {Math.floor(clamped / 10)}
                </div>
            </div>
        </div>
    );
}

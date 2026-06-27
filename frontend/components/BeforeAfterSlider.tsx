"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize } from "lucide-react";
import PixelButton from "./PixelButton";

interface BeforeAfterSliderProps {
    beforeUrl: string;
    afterUrl: string;
}

type CompareMode = "slider" | "side-by-side" | "toggle";

export default function BeforeAfterSlider({
    beforeUrl,
    afterUrl,
}: BeforeAfterSliderProps) {
    const [mode, setMode] = useState<CompareMode>("slider");
    const [sliderPos, setSliderPos] = useState(50);
    const [isDragging, setIsDragging] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isMuted, setIsMuted] = useState(true);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [progress, setProgress] = useState(0);
    const [showBeforeToggle, setShowBeforeToggle] = useState(false);

    const containerRef = useRef<HTMLDivElement>(null);
    const beforeVideoRef = useRef<HTMLVideoElement>(null);
    const afterVideoRef = useRef<HTMLVideoElement>(null);
    const isSeekingRef = useRef(false);

    // Sync play/pause state
    useEffect(() => {
        const vBefore = beforeVideoRef.current;
        const vAfter = afterVideoRef.current;
        if (!vBefore || !vAfter) return;

        if (isPlaying) {
            vBefore.play().catch(() => {});
            vAfter.play().catch(() => {});
        } else {
            vBefore.pause();
            vAfter.pause();
        }
    }, [isPlaying]);

    // Keep videos synchronized periodically
    useEffect(() => {
        const interval = setInterval(() => {
            const vBefore = beforeVideoRef.current;
            const vAfter = afterVideoRef.current;
            if (!vBefore || !vAfter || isSeekingRef.current) return;

            // Check divergence
            const diff = Math.abs(vBefore.currentTime - vAfter.currentTime);
            if (diff > 0.08) {
                vBefore.currentTime = vAfter.currentTime;
            }
        }, 100);

        return () => clearInterval(interval);
    }, []);

    // Sync play speed / playbackrate
    const handleLoadedMetadata = () => {
        const vAfter = afterVideoRef.current;
        if (vAfter && !isNaN(vAfter.duration)) {
            setDuration(vAfter.duration);
        }
    };

    const handleTimeUpdate = () => {
        const vAfter = afterVideoRef.current;
        if (!vAfter || isSeekingRef.current) return;

        setCurrentTime(vAfter.currentTime);
        if (duration > 0) {
            setProgress((vAfter.currentTime / duration) * 100);
        }
    };

    const togglePlay = () => {
        setIsPlaying(!isPlaying);
    };

    const toggleMute = () => {
        setIsMuted(!isMuted);
    };

    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        isSeekingRef.current = true;
        const val = parseFloat(e.target.value);
        setProgress(val);

        const seekTime = (val / 100) * duration;
        setCurrentTime(seekTime);

        const vBefore = beforeVideoRef.current;
        const vAfter = afterVideoRef.current;
        if (vBefore) vBefore.currentTime = seekTime;
        if (vAfter) vAfter.currentTime = seekTime;
    };

    const handleSeekEnd = () => {
        isSeekingRef.current = false;
    };

    // Pointer events for reveal slider dragging
    const handlePointerDown = () => {
        setIsDragging(true);
    };

    const handlePointerUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    const handlePointerMove = useCallback(
        (e: React.PointerEvent) => {
            if (!isDragging || !containerRef.current || mode !== "slider") return;
            const rect = containerRef.current.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
            setSliderPos(pct);
        },
        [isDragging, mode]
    );

    useEffect(() => {
        if (isDragging) {
            window.addEventListener("pointerup", handlePointerUp);
        } else {
            window.removeEventListener("pointerup", handlePointerUp);
        }
        return () => window.removeEventListener("pointerup", handlePointerUp);
    }, [isDragging, handlePointerUp]);

    const formatTime = (time: number) => {
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };

    return (
        <div className="w-full flex flex-col gap-4">
            {/* Mode Controls */}
            <div className="flex justify-between items-center bg-[var(--bg-glass)] border-2 border-[var(--border-pixel)] p-2 rounded">
                <div className="flex gap-2">
                    {(["slider", "side-by-side", "toggle"] as const).map((m) => (
                        <button
                            key={m}
                            onClick={() => setMode(m)}
                            className={`font-pixel text-[8px] px-3 py-1.5 border-2 uppercase transition-all ${
                                mode === m
                                    ? "bg-[var(--mc-emerald)] border-[var(--mc-grass-dark)] text-white shadow-[0_0_8px_rgba(23,221,98,0.4)]"
                                    : "bg-[var(--mc-stone)] border-[var(--mc-stone-dark)] text-[var(--text-primary)] hover:bg-[var(--mc-stone-light)]"
                            }`}
                        >
                            {m.replace("-", " ")}
                        </button>
                    ))}
                </div>

                {mode === "toggle" && (
                    <button
                        onClick={() => setShowBeforeToggle(!showBeforeToggle)}
                        className={`font-pixel text-[8px] px-3 py-1.5 border-2 uppercase transition-all ${
                            showBeforeToggle
                                ? "bg-[var(--mc-redstone)] border-[#991010] text-white"
                                : "bg-[var(--mc-emerald)] border-[var(--mc-grass-dark)] text-white"
                        }`}
                    >
                        {showBeforeToggle ? "◄ BEFORE (ORIGINAL)" : "AFTER (PROCESSED) ►"}
                    </button>
                )}
            </div>

            {/* Video Container Area */}
            <div
                ref={containerRef}
                className="relative w-full aspect-video overflow-hidden border-4 border-[var(--border-pixel)] bg-black select-none touch-none"
                onPointerMove={handlePointerMove}
                onPointerDown={mode === "slider" ? handlePointerDown : undefined}
            >
                {/* Labels overlay */}
                {mode !== "side-by-side" && (
                    <div className="absolute top-2 left-2 right-2 flex justify-between pointer-events-none z-20">
                        {(mode === "slider" || showBeforeToggle) && (
                            <span className="font-pixel text-[8px] bg-black/60 px-2 py-1 rounded border border-[var(--mc-redstone)] mc-text-glow-redstone">
                                ◄ BEFORE
                            </span>
                        )}
                        {(mode === "slider" || !showBeforeToggle) && (
                            <span className="font-pixel text-[8px] bg-black/60 px-2 py-1 rounded border border-[var(--mc-emerald)] mc-text-glow-green ml-auto">
                                AFTER ►
                            </span>
                        )}
                    </div>
                )}

                {/* ── Slider Mode ── */}
                {mode === "slider" && (
                    <>
                        {/* Processed (After) on Bottom */}
                        <video
                            ref={afterVideoRef}
                            src={afterUrl}
                            className="absolute inset-0 w-full h-full object-cover"
                            loop
                            muted={isMuted}
                            playsInline
                            onLoadedMetadata={handleLoadedMetadata}
                            onTimeUpdate={handleTimeUpdate}
                        />

                        {/* Original (Before) on Top with clipPath */}
                        <div
                            className="absolute inset-0 overflow-hidden"
                            style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
                        >
                            <video
                                ref={beforeVideoRef}
                                src={beforeUrl}
                                className="absolute inset-0 w-full h-full object-cover"
                                loop
                                muted={true}
                                playsInline
                            />
                        </div>

                        {/* Slider Handle line */}
                        <div
                            className="mc-slider-handle absolute top-0 bottom-0 z-10"
                            style={{ left: `${sliderPos}%`, transform: "translateX(-50%)" }}
                            onPointerDown={handlePointerDown}
                        >
                            <div
                                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded border-2 border-[var(--mc-emerald)] flex items-center justify-center cursor-ew-resize"
                                style={{
                                    background: "rgba(23, 221, 98, 0.2)",
                                    boxShadow: "var(--glow-green)",
                                }}
                            >
                                <span className="font-pixel text-[8px] text-[var(--mc-emerald)]">
                                    ⇔
                                </span>
                            </div>
                        </div>
                    </>
                )}

                {/* ── Side-by-Side Mode ── */}
                {mode === "side-by-side" && (
                    <div className="absolute inset-0 flex">
                        <div className="relative w-1/2 h-full border-r-2 border-[var(--border-pixel)]">
                            <video
                                ref={beforeVideoRef}
                                src={beforeUrl}
                                className="w-full h-full object-cover"
                                loop
                                muted={true}
                                playsInline
                            />
                            <span className="absolute bottom-2 left-2 font-pixel text-[8px] bg-black/60 px-2 py-1 rounded border border-[var(--mc-redstone)] mc-text-glow-redstone">
                                BEFORE
                            </span>
                        </div>
                        <div className="relative w-1/2 h-full">
                            <video
                                ref={afterVideoRef}
                                src={afterUrl}
                                className="w-full h-full object-cover"
                                loop
                                muted={isMuted}
                                playsInline
                                onLoadedMetadata={handleLoadedMetadata}
                                onTimeUpdate={handleTimeUpdate}
                            />
                            <span className="absolute bottom-2 right-2 font-pixel text-[8px] bg-black/60 px-2 py-1 rounded border border-[var(--mc-emerald)] mc-text-glow-green">
                                AFTER
                            </span>
                        </div>
                    </div>
                )}

                {/* ── Toggle Mode ── */}
                {mode === "toggle" && (
                    <>
                        <video
                            ref={afterVideoRef}
                            src={afterUrl}
                            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${
                                showBeforeToggle ? "opacity-0" : "opacity-100"
                            }`}
                            loop
                            muted={isMuted}
                            playsInline
                            onLoadedMetadata={handleLoadedMetadata}
                            onTimeUpdate={handleTimeUpdate}
                        />
                        <video
                            ref={beforeVideoRef}
                            src={beforeUrl}
                            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${
                                showBeforeToggle ? "opacity-100" : "opacity-0"
                            }`}
                            loop
                            muted={true}
                            playsInline
                        />
                    </>
                )}
            </div>

            {/* Custom Video Controls */}
            <div className="mc-panel p-4 flex flex-col gap-3">
                {/* Timeline / Progress scrubber */}
                <div className="flex items-center gap-3">
                    <span className="font-pixel text-[8px] text-[var(--text-primary)] w-12 text-left">
                        {formatTime(currentTime)}
                    </span>
                    <div className="flex-1 relative h-3 bg-[var(--mc-stone-dark)] border-2 border-[var(--border-pixel)] overflow-hidden cursor-pointer">
                        <input
                            type="range"
                            min="0"
                            max="100"
                            step="0.1"
                            value={progress}
                            onChange={handleSeek}
                            onMouseUp={handleSeekEnd}
                            onTouchEnd={handleSeekEnd}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />
                        <div
                            className="absolute inset-y-0 left-0 bg-[var(--mc-emerald)] shadow-[0_0_8px_rgba(23,221,98,0.5)] transition-all"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <span className="font-pixel text-[8px] text-[var(--text-primary)] w-12 text-right">
                        {formatTime(duration)}
                    </span>
                </div>

                {/* Playback Controls & Volume */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={togglePlay}
                            className="text-white hover:text-[var(--mc-emerald)] transition-colors"
                        >
                            {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 fill-current" />}
                        </button>
                        <button
                            onClick={toggleMute}
                            className="text-white hover:text-[var(--mc-gold)] transition-colors"
                        >
                            {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                        </button>
                    </div>

                    <span className="font-pixel text-[6px] text-[var(--text-muted)]">
                        * Muted BEFORE audio automatically to prevent echo
                    </span>
                </div>
            </div>
        </div>
    );
}

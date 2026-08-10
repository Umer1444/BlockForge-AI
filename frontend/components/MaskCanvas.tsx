"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import PixelButton from "./PixelButton";

interface MaskCanvasProps {
    imageUrl: string;
    onSave: (maskDataUrl: string) => void;
    width: number;
    height: number;
}

export default function MaskCanvas({
    imageUrl,
    onSave,
    width,
    height,
}: MaskCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const maskCanvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [brushSize, setBrushSize] = useState(30);
    const [tool, setTool] = useState<"brush" | "eraser">("brush");
    const [bgLoaded, setBgLoaded] = useState(false);
    const [history, setHistory] = useState<ImageData[]>([]);

    // Display dimensions (fit within container)
    const maxW = 900;
    const maxH = 550;
    const scale = Math.min(maxW / width, maxH / height, 1);
    const displayW = Math.round(width * scale);
    const displayH = Math.round(height * scale);

    // Reset history when image or canvas dimensions change
    useEffect(() => {
        setHistory([]);
    }, [imageUrl, displayW, displayH]);

    // Load background image
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            ctx.drawImage(img, 0, 0, displayW, displayH);
            setBgLoaded(true);
        };
        img.src = imageUrl;
    }, [imageUrl, displayW, displayH]);

    // Initialize mask canvas
    useEffect(() => {
        const maskCanvas = maskCanvasRef.current;
        if (!maskCanvas) return;

        const ctx = maskCanvas.getContext("2d");
        if (!ctx) return;

        ctx.clearRect(0, 0, displayW, displayH);
    }, [displayW, displayH]);

    const saveStateToHistory = useCallback(() => {
        const maskCanvas = maskCanvasRef.current;
        if (!maskCanvas) return;
        const ctx = maskCanvas.getContext("2d");
        if (!ctx || typeof ctx.getImageData !== "function") return;
        try {
            const imageData = ctx.getImageData(0, 0, displayW, displayH);
            setHistory((prev) => [...prev.slice(-9), imageData]);
        } catch {
            // Ignore canvas context errors in headless test environments
        }
    }, [displayW, displayH]);

    const handleUndo = useCallback(() => {
        if (history.length === 0) return;
        const maskCanvas = maskCanvasRef.current;
        if (!maskCanvas) return;
        const ctx = maskCanvas.getContext("2d");
        const lastState = history[history.length - 1];

        if (ctx && lastState && typeof ctx.putImageData === "function") {
            try {
                ctx.putImageData(lastState, 0, 0);
            } catch {
                // Ignore canvas context errors in headless test environments
            }
        }
        setHistory((prev) => prev.slice(0, -1));
    }, [history]);

    const getPos = (e: React.MouseEvent) => {
        const rect = maskCanvasRef.current?.getBoundingClientRect();
        if (!rect) return { x: 0, y: 0 };
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
        };
    };

    const draw = useCallback(
        (x: number, y: number) => {
            const ctx = maskCanvasRef.current?.getContext("2d");
            if (!ctx) return;

            ctx.globalCompositeOperation =
                tool === "brush" ? "source-over" : "destination-out";
            ctx.beginPath();
            ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(255, 0, 0, 0.5)";
            ctx.fill();
        },
        [tool, brushSize]
    );

    const handleMouseDown = (e: React.MouseEvent) => {
        saveStateToHistory();
        setIsDrawing(true);
        const { x, y } = getPos(e);
        draw(x, y);
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDrawing) return;
        const { x, y } = getPos(e);
        draw(x, y);
    };

    const handleMouseUp = () => setIsDrawing(false);

    const clearMask = useCallback(() => {
        saveStateToHistory();
        const ctx = maskCanvasRef.current?.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, displayW, displayH);
    }, [displayW, displayH, saveStateToHistory]);

    // Keyboard Shortcuts Listener
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement | null;
            if (
                target &&
                (target.tagName === "TEXTAREA" ||
                    (target.tagName === "INPUT" && (target as HTMLInputElement).type !== "range") ||
                    target.isContentEditable)
            ) {
                return;
            }

            if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) {
                e.preventDefault();
                handleUndo();
                return;
            }

            if (e.ctrlKey || e.metaKey || e.altKey) {
                return;
            }

            if (e.key === "b" || e.key === "B") {
                e.preventDefault();
                setTool("brush");
            } else if (e.key === "e" || e.key === "E") {
                e.preventDefault();
                setTool("eraser");
            } else if (e.key === "[") {
                e.preventDefault();
                setBrushSize((prev) => Math.max(5, prev - 5));
            } else if (e.key === "]") {
                e.preventDefault();
                setBrushSize((prev) => Math.min(100, prev + 5));
            } else if (e.key === "Escape") {
                e.preventDefault();
                clearMask();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => {
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [handleUndo, clearMask]);

    const saveMask = () => {
        const maskCanvas = maskCanvasRef.current;
        if (!maskCanvas) return;

        // Create output mask at original resolution
        const outputCanvas = document.createElement("canvas");
        outputCanvas.width = width;
        outputCanvas.height = height;
        const outCtx = outputCanvas.getContext("2d")!;

        // Draw mask scaled to original resolution
        outCtx.drawImage(maskCanvas, 0, 0, width, height);

        // Convert red mask to white-on-black binary mask
        const imageData = outCtx.getImageData(0, 0, width, height);
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const hasColor = data[i] > 50; // Red channel
            data[i] = hasColor ? 255 : 0;     // R
            data[i + 1] = hasColor ? 255 : 0; // G
            data[i + 2] = hasColor ? 255 : 0; // B
            data[i + 3] = 255;                // A
        }
        outCtx.putImageData(imageData, 0, 0);

        onSave(outputCanvas.toDataURL("image/png"));
    };

    return (
        <div className="flex flex-col items-center gap-4 p-4 w-full">
            {/* Toolbar */}
            <div
                role="toolbar"
                aria-label="Canvas toolbar"
                className="flex items-center gap-3 flex-wrap"
            >
                <PixelButton
                    variant={tool === "brush" ? "grass" : "stone"}
                    size="sm"
                    onClick={() => setTool("brush")}
                    aria-label="Brush tool"
                    aria-pressed={tool === "brush"}
                    title="Switch to Brush tool (B)"
                >
                    🖌 Brush
                </PixelButton>
                <PixelButton
                    variant={tool === "eraser" ? "redstone" : "stone"}
                    size="sm"
                    onClick={() => setTool("eraser")}
                    aria-label="Eraser tool"
                    aria-pressed={tool === "eraser"}
                    title="Switch to Eraser tool (E)"
                >
                    🧽 Eraser
                </PixelButton>

                <div className="flex items-center gap-2 ml-4">
                    <span className="font-pixel text-[8px] text-[var(--text-secondary)]">
                        Size:
                    </span>
                    <input
                        type="range"
                        min={5}
                        max={100}
                        value={brushSize}
                        onChange={(e) => setBrushSize(parseInt(e.target.value))}
                        className="w-24 accent-[var(--mc-emerald)]"
                        aria-label="Brush size"
                        aria-valuenow={brushSize}
                        aria-valuemin={5}
                        aria-valuemax={100}
                        title="Adjust brush size ([ / ])"
                    />
                    <span className="font-pixel text-[8px] text-[var(--text-primary)]">
                        {brushSize}px
                    </span>
                </div>

                <PixelButton
                    variant="stone"
                    size="sm"
                    onClick={handleUndo}
                    disabled={history.length === 0}
                    aria-label="Undo last stroke"
                    title="Undo last mask stroke (Ctrl+Z / Cmd+Z)"
                    className="ml-4"
                >
                    ↩ Undo
                </PixelButton>
                <PixelButton
                    variant="stone"
                    size="sm"
                    onClick={clearMask}
                    aria-label="Clear mask"
                    title="Clear current mask canvas (Esc)"
                >
                    🗑 Clear
                </PixelButton>
                <PixelButton
                    variant="diamond"
                    size="sm"
                    onClick={saveMask}
                    aria-label="Save mask"
                    title="Save mask"
                >
                    ✅ Save Mask
                </PixelButton>
            </div>

            {/* Canvas Area */}
            <div
                ref={containerRef}
                className="relative border-2 border-[var(--border-pixel)]"
                style={{ width: displayW, height: displayH }}
            >
                {/* Background image */}
                <canvas
                    ref={canvasRef}
                    width={displayW}
                    height={displayH}
                    className="absolute top-0 left-0"
                />
                {/* Mask layer */}
                <canvas
                    ref={maskCanvasRef}
                    width={displayW}
                    height={displayH}
                    role="img"
                    aria-label="Inpainting mask drawing canvas"
                    className="absolute top-0 left-0 cursor-crosshair"
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                />
            </div>

            <p className="font-pixel text-[8px] text-[var(--text-muted)] text-center">
                Paint over the area to remove, then click Save Mask
            </p>
            <p className="font-pixel text-[8px] text-[var(--text-secondary)] text-center opacity-80">
                Shortcuts: <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">B</kbd> Brush | <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">E</kbd> Eraser | <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">[</kbd> / <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">]</kbd> Size (-/+ 5px) | <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">Ctrl+Z</kbd> Undo | <kbd className="px-1 py-0.5 bg-[var(--bg-pixel)] rounded border border-[var(--border-pixel)]">Esc</kbd> Clear
            </p>
        </div>
    );
}

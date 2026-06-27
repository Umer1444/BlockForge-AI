"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";

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

    // Display dimensions (fit within container)
    const maxW = 900;
    const maxH = 550;
    const scale = Math.min(maxW / width, maxH / height, 1);
    const displayW = Math.round(width * scale);
    const displayH = Math.round(height * scale);

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

    const clearMask = () => {
        const ctx = maskCanvasRef.current?.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, displayW, displayH);
    };

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
            <div className="flex items-center gap-3 flex-wrap">
                <button
                    onClick={() => setTool("brush")}
                    className={`mc-btn ${tool === "brush" ? "mc-btn-grass" : "mc-btn-stone"
                        } text-[9px] px-3 py-2`}
                >
                    🖌 Brush
                </button>
                <button
                    onClick={() => setTool("eraser")}
                    className={`mc-btn ${tool === "eraser" ? "mc-btn-redstone" : "mc-btn-stone"
                        } text-[9px] px-3 py-2`}
                >
                    🧽 Eraser
                </button>

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
                    />
                    <span className="font-pixel text-[8px] text-[var(--text-primary)]">
                        {brushSize}px
                    </span>
                </div>

                <button
                    onClick={clearMask}
                    className="mc-btn mc-btn-stone text-[9px] px-3 py-2 ml-4"
                >
                    🗑 Clear
                </button>
                <button
                    onClick={saveMask}
                    className="mc-btn mc-btn-diamond text-[9px] px-3 py-2"
                >
                    ✅ Save Mask
                </button>
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
                    className="absolute top-0 left-0 cursor-crosshair"
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                />
            </div>

            <p className="font-pixel text-[8px] text-[var(--text-muted)]">
                Paint over the area to remove, then click Save Mask
            </p>
        </div>
    );
}

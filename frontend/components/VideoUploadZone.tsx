"use client";

import React, { useState, useCallback, useRef } from "react";
import PixelButton from "./PixelButton";

interface VideoUploadZoneProps {
    apiUrl: string;
    onUploadComplete: (data: { job_id: string; metadata: any }) => void;
}

export default function VideoUploadZone({
    apiUrl,
    onUploadComplete,
}: VideoUploadZoneProps) {
    const [isDragOver, setIsDragOver] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const validExtensions = ["mp4", "avi", "mov", "mkv", "webm"];

    const validateFile = (f: File): boolean => {
        const ext = f.name.split(".").pop()?.toLowerCase() || "";
        if (!validExtensions.includes(ext)) {
            setError(`Unsupported format: .${ext}`);
            return false;
        }
        if (f.size > 500 * 1024 * 1024) {
            setError("File too large (max 500 MB)");
            return false;
        }
        setError(null);
        return true;
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && validateFile(droppedFile)) {
            setFile(droppedFile);
        }
    }, []);

    const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0];
        if (selected && validateFile(selected)) {
            setFile(selected);
        }
    };

    const uploadFile = async () => {
        if (!file) return;

        setUploading(true);
        setUploadProgress(0);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    setUploadProgress(Math.round((e.loaded / e.total) * 100));
                }
            });

            const result = await new Promise<any>((resolve, reject) => {
                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(xhr.responseText));
                    }
                };
                xhr.onerror = () => reject(new Error("Upload failed"));
                xhr.open("POST", `${apiUrl}/api/upload`);
                xhr.send(formData);
            });

            onUploadComplete(result);
        } catch (err: any) {
            setError(err.message || "Upload failed");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-8">
            {!file ? (
                /* ── Drop Zone ── */
                <div
                    className={`w-full max-w-lg border-4 border-dashed rounded p-12 text-center cursor-pointer transition-all duration-200 ${isDragOver
                            ? "border-[var(--mc-emerald)] bg-[rgba(23,221,98,0.05)]"
                            : "border-[var(--border-pixel)] hover:border-[var(--mc-diamond)]"
                        }`}
                    onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragOver(true);
                    }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                >
                    <input
                        ref={inputRef}
                        type="file"
                        accept="video/*"
                        className="hidden"
                        onChange={handleSelect}
                    />

                    <div className="text-5xl mb-4">
                        {isDragOver ? "📥" : "🎬"}
                    </div>
                    <p className="font-pixel text-xs text-[var(--text-primary)] mb-2">
                        {isDragOver ? "DROP IT!" : "DROP VIDEO HERE"}
                    </p>
                    <p className="font-pixel text-[8px] text-[var(--text-muted)]">
                        or click to browse • MP4, AVI, MOV, MKV, WebM • Max 500MB
                    </p>
                </div>
            ) : (
                /* ── File Selected ── */
                <div className="w-full max-w-lg mc-panel p-6 text-center space-y-4">
                    <div className="text-4xl">📼</div>
                    <p className="font-pixel text-xs text-[var(--text-primary)] truncate">
                        {file.name}
                    </p>
                    <p className="font-pixel text-[9px] text-[var(--text-secondary)]">
                        {(file.size / (1024 * 1024)).toFixed(1)} MB
                    </p>

                    {uploading && (
                        <div className="mc-xp-bar rounded-sm">
                            <div
                                className="mc-xp-fill mc-shine"
                                style={{ width: `${uploadProgress}%` }}
                            />
                        </div>
                    )}

                    <div className="flex gap-3 justify-center">
                        <PixelButton
                            variant="grass"
                            onClick={uploadFile}
                            disabled={uploading}
                        >
                            {uploading
                                ? `⛏ ${uploadProgress}%`
                                : "⬆️ UPLOAD"}
                        </PixelButton>
                        <PixelButton
                            variant="stone"
                            onClick={() => {
                                setFile(null);
                                setError(null);
                            }}
                            disabled={uploading}
                        >
                            ✖ CANCEL
                        </PixelButton>
                    </div>
                </div>
            )}

            {error && (
                <div className="mt-4 mc-panel p-3 border-[var(--mc-redstone)]">
                    <p className="font-pixel text-[9px] mc-text-glow-redstone">
                        ❌ {error}
                    </p>
                </div>
            )}
        </div>
    );
}

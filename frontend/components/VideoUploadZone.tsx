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
    const [files, setFiles] = useState<File[]>([]);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [currentFileIndex, setCurrentFileIndex] = useState(0);
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
        const droppedFiles = Array.from(e.dataTransfer.files);
        const validFiles = droppedFiles.filter(validateFile);
        if (validFiles.length > 0) {
            setFiles(prev => [...prev, ...validFiles]);
        }
    }, []);

    const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files || []);
        const validFiles = selectedFiles.filter(validateFile);
        if (validFiles.length > 0) {
            setFiles(prev => [...prev, ...validFiles]);
        }
    };

    const uploadFile = async () => {
        if (files.length === 0) return;

        setUploading(true);
        setError(null);
        let firstResult: any = null;

        for (let i = 0; i < files.length; i++) {
            const currentFile = files[i];
            setCurrentFileIndex(i);
            setUploadProgress(0);

            try {
                const formData = new FormData();
                formData.append("file", currentFile);

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

                if (i === 0) {
                    firstResult = result;
                }
            } catch (err: any) {
                setError(`Upload failed for ${currentFile.name}: ${err.message}`);
                break;
            }
        }

        setUploading(false);
        setFiles([]);
        
        // Pass the first result to the parent to make it active, the rest will be in the history
        if (firstResult) {
            onUploadComplete(firstResult);
        }
    };

    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-8">
            {!files.length ? (
                /* ── Drop Zone ── */
                <div
                    className={`w-full max-w-lg border-4 border-dashed rounded p-12 text-center cursor-pointer transition-all duration-200 ${isDragOver
                            ? "border-[var(--mc-emerald)] bg-[rgba(23,221,98,0.05)]"
                            : "border-[var(--border-color)] hover:border-[var(--mc-emerald)]"
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
                        type="file"
                        ref={inputRef}
                        onChange={handleSelect}
                        className="hidden"
                        accept={validExtensions.map((e) => `.${e}`).join(",")}
                        multiple
                    />
                    <div className="text-4xl mb-4">📥</div>
                    <h3 className="text-xl font-bold text-white mb-2">
                        Upload Video(s)
                    </h3>
                    <p className="text-[var(--text-color)] text-sm mb-4">
                        Drag & drop your files here, or click to browse
                    </p>
                    <p className="text-xs text-[var(--text-color)] opacity-70">
                        Supports {validExtensions.join(", ")} up to 500MB each
                    </p>
                </div>
            ) : (
                /* ── Uploading / Ready State ── */
                <div className="w-full max-w-lg bg-[var(--surface-color)] border border-[var(--border-color)] p-8 rounded shadow-lg flex flex-col items-center">
                    <div className="text-4xl mb-4 text-[var(--mc-emerald)]">🎥</div>
                    <h3 className="text-xl font-bold text-white mb-2">
                        {files.length} File(s) Selected
                    </h3>
                    <div className="w-full max-h-32 overflow-y-auto mb-6 text-sm text-[var(--text-color)]">
                        {files.map((f, idx) => (
                            <div key={idx} className="flex justify-between items-center bg-[var(--bg-color)] p-2 mb-1 rounded">
                                <span className="truncate">{f.name}</span>
                                <span>{(f.size / (1024 * 1024)).toFixed(1)} MB</span>
                            </div>
                        ))}
                    </div>

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
                                setFiles([]);
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

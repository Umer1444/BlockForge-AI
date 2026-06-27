"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import VideoUploadZone from "../../components/VideoUploadZone";
import MaskCanvas from "../../components/MaskCanvas";
import XPProgressBar from "../../components/XPProgressBar";
import CraftingLoader from "../../components/CraftingLoader";
import dynamic from "next/dynamic";
const BeforeAfterSlider = dynamic(() => import("../../components/BeforeAfterSlider"), { ssr: false });
import PixelButton from "../../components/PixelButton";
import HistoryCard, { HistoryItem } from "../../components/HistoryCard";
import VideoPreviewModal from "../../components/VideoPreviewModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type JobState = "idle" | "uploaded" | "masking" | "processing" | "completed" | "failed";

interface JobMetadata {
    job_id: string;
    width: number;
    height: number;
    fps: number;
    duration: number;
    total_frames: number;
    original_filename: string;
}

// HistoryItem moved to HistoryCard.tsx

export default function Dashboard() {
    const [jobState, setJobState] = useState<JobState>("idle");
    const [metadata, setMetadata] = useState<JobMetadata | null>(null);
    const [progress, setProgress] = useState(0);
    const [statusText, setStatusText] = useState("Awaiting upload...");
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [maskDataUrl, setMaskDataUrl] = useState<string | null>(null);
    const [outputUrl, setOutputUrl] = useState<string | null>(null);
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [clearedJobs, setClearedJobs] = useState<Set<string>>(new Set());
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [previewItem, setPreviewItem] = useState<HistoryItem | null>(null);

    const [processOptions, setProcessOptions] = useState({
        useEnhancement: false,
        crf: 18,
        codec: "libx264",
    });
    const wsRef = useRef<WebSocket | null>(null);

    // ── Load Cleared Jobs from LocalStorage ──
    useEffect(() => {
        const stored = localStorage.getItem("blockforge_cleared_jobs");
        if (stored) {
            try {
                setClearedJobs(new Set(JSON.parse(stored)));
            } catch (e) {
                console.error("Failed to parse cleared jobs", e);
            }
        }
    }, []);

    // ── Fetch History ──
    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/jobs`);
            const data = await res.json();
            // Filter out items that are in clearedJobs
            const filtered = (data.jobs || []).filter((item: HistoryItem) => !clearedJobs.has(item.job_id));
            setHistory(filtered);
        } catch (err) {
            console.error("Failed to fetch history:", err);
        } finally {
            setIsLoadingHistory(false);
        }
    }, [clearedJobs]);

    useEffect(() => {
        fetchHistory();
        const timer = setInterval(fetchHistory, 5000); // Polling for updates
        return () => clearInterval(timer);
    }, [fetchHistory]);

    // ── Handle Upload Complete ──
    const handleUploadComplete = useCallback(
        (data: { job_id: string; metadata: JobMetadata }) => {
            setMetadata(data.metadata as unknown as JobMetadata);
            setJobState("uploaded");
            setStatusText("Video uploaded! Draw a mask or use AI segmentation.");
            // Fetch preview frame
            setPreviewUrl(`${API_URL}/api/upload/${data.job_id}/frame?time=0`);
            fetchHistory();
        },
        [fetchHistory]
    );

    // ── Handle Mask Save ──
    const handleMaskSave = useCallback((dataUrl: string) => {
        setMaskDataUrl(dataUrl);
        setJobState("masking");
        setStatusText("Mask ready. Click Process to begin!");
    }, []);

    // ── Start Processing ──
    const startProcessing = useCallback(async () => {
        if (!metadata || !maskDataUrl) return;

        setJobState("processing");
        setProgress(0);
        setStatusText("Queuing job...");

        try {
            // Extract base64 from data URL
            const base64 = maskDataUrl.split(",")[1];

            const res = await fetch(`${API_URL}/api/process`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    job_id: metadata.job_id,
                    mask_base64: base64,
                    use_enhancement: processOptions.useEnhancement,
                    crf: processOptions.crf,
                    codec: processOptions.codec,
                }),
            });

            await res.json();

            // Connect WebSocket
            const wsUrl = `${API_URL.replace(/^http/, "ws")}/ws/${metadata.job_id}`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                setProgress(msg.progress || 0);
                setStatusText(msg.current_step || "Processing...");

                if (msg.state === "completed") {
                    setJobState("completed");
                    const finalOutputUrl = msg.details?.output_url
                        ? `${API_URL}${msg.details.output_url}`
                        : null;
                    const finalPreviewAfterUrl = msg.details?.preview_after_url
                        ? `${API_URL}${msg.details.preview_after_url}`
                        : null;

                    setOutputUrl(finalOutputUrl);
                    // Use preview_after_url from message if available
                    if (finalPreviewAfterUrl) {
                        setPreviewUrl(finalPreviewAfterUrl);
                    }
                    ws.close();
                    fetchHistory();
                } else if (msg.state === "failed") {
                    setJobState("failed");
                    setStatusText(`Failed: ${msg.current_step}`);
                    ws.close();
                    fetchHistory();
                }
            };

            ws.onerror = () => {
                setStatusText("WebSocket connection error");
                setJobState("failed");
            };
        } catch (err) {
            setStatusText(`Error: ${err}`);
            setJobState("failed");
        }
    }, [metadata, maskDataUrl, processOptions, fetchHistory]);

    // ── Recall Job ──
    const recallJob = useCallback(async (job: HistoryItem) => {
        // Reset state first
        resetJob();

        // Load metadata
        try {
            const res = await fetch(`${API_URL}/api/status/${job.job_id}`);
            const data = await res.json();

            // If the status has output, we skip masking
            if (data.output_ready) {
                setJobState("completed");
                const finalUrl = `${API_URL}${data.output_url}`;
                setOutputUrl(finalUrl);
                setPreviewUrl(`${API_URL}${data.preview_url || data.details?.preview_after_url}`);

                // ── Auto-Download ──
                const a = document.createElement('a');
                a.href = finalUrl;
                a.download = `blockforge_${data.filename || 'reconstructed'}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                setJobState("uploaded");
                setPreviewUrl(`${API_URL}/api/upload/${job.job_id}/frame?time=0`);
            }

            setMetadata({
                job_id: data.job_id,
                original_filename: data.filename || "Recovered Video",
                width: parseInt((data.resolution || "0x0").split("x")[0]) || 0,
                height: parseInt((data.resolution || "0x0").split("x")[1]) || 0,
                duration: data.duration || 0,
                fps: 24, // Estimate
                total_frames: 0
            } as JobMetadata);

            setStatusText(data.output_ready ? "Forge restored & downloading." : "Draft restored. Ready for masking.");
        } catch (err) {
            console.error("Failed to recall job:", err);
        }
    }, [resetJob]);

    // ── Delete Job (Backend + Registry) ──
    const handleDeleteJob = useCallback(async (e: React.MouseEvent, item: HistoryItem) => {
        e.stopPropagation();
        if (!confirm(`Permanently delete ${item.filename || 'this forge'} from the registry?`)) return;

        try {
            const res = await fetch(`${API_URL}/api/jobs/${item.job_id}`, { method: "DELETE" });
            if (res.ok) {
                // If it was the active job, reset
                if (metadata?.job_id === item.job_id) {
                    resetJob();
                }
                fetchHistory();
            } else {
                console.error("Failed to delete job");
            }
        } catch (err) {
            console.error("Error deleting job:", err);
        }
    }, [metadata, fetchHistory]);

    // ── Cancel Processing ──
    const handleCancelProcessing = useCallback(async () => {
        if (!metadata) return;
        setStatusText("Cancelling...");

        try {
            const res = await fetch(`${API_URL}/api/jobs/${metadata.job_id}/cancel`, { method: "POST" });
            if (res.ok) {
                setStatusText("Processing cancelled.");
                setJobState("failed");
                wsRef.current?.close();
                fetchHistory();
            }
        } catch (err) {
            console.error("Error cancelling job:", err);
            setStatusText("Failed to cancel.");
        }
    }, [metadata, fetchHistory]);

    // ── Clear History (Frontend Only) ──
    const clearHistory = () => {
        if (!confirm("This will clear your local history view only. Backend files will remain untouched. Proceed?")) return;

        const allJobIdsInHistory = history.map(item => item.job_id);
        const newClearedSet = new Set([...Array.from(clearedJobs), ...allJobIdsInHistory]);

        setClearedJobs(newClearedSet);
        localStorage.setItem("blockforge_cleared_jobs", JSON.stringify(Array.from(newClearedSet)));

        setHistory([]);
    };

    // Cleanup WebSocket
    useEffect(() => {
        return () => {
            wsRef.current?.close();
        };
    }, []);

    // Reset
    function resetJob() {
        setJobState("idle");
        setMetadata(null);
        setProgress(0);
        setStatusText("Awaiting upload...");
        setPreviewUrl(null);
        setMaskDataUrl(null);
        setOutputUrl(null);
        wsRef.current?.close();
    }

    return (
        <div className="min-h-screen flex flex-col">
            {/* ── Top Bar ── */}
            <header className="mc-panel-header flex items-center justify-between px-6">
                <Link href="/" className="flex items-center gap-3">
                    <span className="text-2xl">⛏️</span>
                    <h1 className="font-pixel text-sm text-white">
                        BLOCK<span className="mc-text-glow-green">FORGE</span>
                    </h1>
                </Link>
                <div className="flex items-center gap-6">
                    <div className="font-pixel text-[10px] text-[var(--text-secondary)]">
                        {metadata
                            ? `${metadata.width}×${metadata.height} · ${metadata.fps}fps · ${Math.round(metadata.duration)}s`
                            : "No video loaded"}
                    </div>
                    <PixelButton variant="stone" size="sm" onClick={resetJob}>
                        🔄 Reset
                    </PixelButton>
                </div>
            </header>

            {/* ── Main Studio ── */}
            <main className="flex-1 p-6 flex gap-6 overflow-hidden">
                {/* ── Left Panel: History Sidebar ── */}
                <aside className="w-64 flex flex-col gap-4">
                    <div className="mc-panel flex-1 flex flex-col min-h-0">
                        <div className="mc-panel-header flex justify-between items-center px-2">
                            <h2 className="font-pixel text-[10px] text-white">📜 REGISTRY</h2>
                            <button
                                onClick={clearHistory}
                                className="font-pixel text-[8px] text-[var(--mc-redstone)] hover:text-white transition-colors"
                                title="Clear all history"
                            >
                                [PRUNE]
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-2 space-y-3 custom-scrollbar">
                            {isLoadingHistory ? (
                                // Minecraft-style Skeleton Loaders
                                [1, 2, 3].map((i) => (
                                    <div key={i} className="mc-panel p-2 animate-pulse">
                                        <div className="aspect-video bg-[var(--mc-stone)]/30 rounded mb-2" />
                                        <div className="h-2 w-2/3 bg-[var(--mc-stone)]/30 rounded" />
                                    </div>
                                ))
                            ) : history.length === 0 ? (
                                <p className="font-pixel text-[8px] text-[var(--text-muted)] text-center mt-8 px-4">
                                    Your forge registry is empty.
                                </p>
                            ) : (
                                history.map((item) => (
                                    <HistoryCard
                                        key={item.job_id}
                                        item={item}
                                        apiUrl={API_URL}
                                        isActive={metadata?.job_id === item.job_id}
                                        onClick={(item) => {
                                            setPreviewItem(item);
                                            setIsPreviewOpen(true);
                                        }}
                                        onDownload={(e, item) => {
                                            e.stopPropagation();
                                            window.open(`${API_URL}/api/status/${item.job_id}/download`, '_blank');
                                        }}
                                        onDelete={handleDeleteJob}
                                    />
                                ))
                            )}
                        </div>
                    </div>
                </aside>

                {/* ── Center Panel: Video / Canvas ── */}
                <div className="flex-1 flex flex-col gap-4">
                    {/* Status */}
                    <div className="mc-panel p-4 flex items-center gap-4">
                        <div
                            className={`w-3 h-3 rounded-full ${jobState === "completed"
                                ? "bg-[var(--mc-emerald)]"
                                : jobState === "processing"
                                    ? "bg-[var(--mc-gold)] mc-craft-pulse"
                                    : jobState === "failed"
                                        ? "bg-[var(--mc-redstone)]"
                                        : "bg-[var(--mc-stone)]"
                                }`}
                        />
                        <span className="font-pixel text-xs text-[var(--text-primary)]">
                            {statusText}
                        </span>
                    </div>

                    {/* XP Progress Bar */}
                    {jobState === "processing" && (
                        <div className="flex flex-col gap-2">
                            <XPProgressBar progress={progress} label={statusText} />
                            <div className="flex justify-end pr-2">
                                <PixelButton variant="redstone" size="sm" onClick={handleCancelProcessing}>
                                    🛑 CANCEL PROCESS
                                </PixelButton>
                            </div>
                        </div>
                    )}

                    {/* Main Viewport */}
                    <div className="mc-panel flex-1 flex items-center justify-center min-h-[400px] relative overflow-hidden bg-[var(--bg-pixel-dark)]">
                        {jobState === "idle" && (
                            <VideoUploadZone
                                apiUrl={API_URL}
                                onUploadComplete={handleUploadComplete}
                            />
                        )}

                        {(jobState === "uploaded" || jobState === "masking") &&
                            previewUrl && (
                                <MaskCanvas
                                    imageUrl={previewUrl}
                                    onSave={handleMaskSave}
                                    width={metadata?.width || 1280}
                                    height={metadata?.height || 720}
                                />
                            )}

                        {jobState === "processing" && <CraftingLoader />}

                        {jobState === "completed" && outputUrl && (
                            <div className="w-full h-full flex flex-col items-center justify-center gap-6 p-6 animate-in fade-in zoom-in duration-500 overflow-y-auto custom-scrollbar">
                                <div className="text-center">
                                    <div className="font-pixel text-lg mc-text-glow-green mb-2">
                                        ✨ FORGE COMPLETE!
                                    </div>
                                    <p className="font-pixel text-[8px] text-[var(--text-secondary)]">
                                        Your video has been reconstructed without watermarks.
                                    </p>
                                </div>

                                {/* Result Summary Card */}
                                <div className="mc-panel bg-[var(--bg-glass)] border-2 border-[var(--border-pixel)] p-4 w-full max-w-2xl text-center space-y-3">
                                    <div className="font-pixel text-xs text-[var(--mc-emerald)] mc-text-glow-green">
                                        ✔ Watermark Removed Successfully
                                    </div>
                                    <div className="font-pixel text-[10px] text-white">
                                        Forge Status: COMPLETE
                                    </div>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 pt-2 border-t border-[var(--border-pixel)]/30 font-pixel text-[8px] text-[var(--text-secondary)]">
                                        <div>
                                            <span className="text-[var(--text-muted)]">RESOLUTION: </span>
                                            <span className="text-white">{metadata ? `${metadata.width}x${metadata.height}` : "Preserved"}</span>
                                        </div>
                                        <div>
                                            <span className="text-[var(--text-muted)]">DURATION: </span>
                                            <span className="text-white">{metadata ? `${metadata.duration.toFixed(1)}s` : "Preserved"}</span>
                                        </div>
                                        <div className="col-span-2 md:col-span-1">
                                            <span className="text-[var(--text-muted)]">STATUS: </span>
                                            <span className="text-[var(--mc-emerald)]">SUCCESS</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="w-full max-w-2xl">
                                    <BeforeAfterSlider
                                        beforeUrl={metadata ? `${API_URL}/uploads/${metadata.job_id}/original.${metadata.original_filename.split(".").pop()?.toLowerCase() || "mp4"}` : ""}
                                        afterUrl={outputUrl}
                                    />
                                </div>

                                <div className="flex gap-4">
                                    <a href={outputUrl} download={`blockforge_${metadata?.original_filename || "processed"}.mp4`}>
                                        <PixelButton variant="diamond" size="lg">
                                            💎 DOWNLOAD VIDEO
                                        </PixelButton>
                                    </a>
                                    <PixelButton variant="stone" size="lg" onClick={resetJob}>
                                        🔄 NEW FORGE
                                    </PixelButton>
                                </div>
                            </div>
                        )}

                        {jobState === "failed" && (
                            <div className="text-center p-8">
                                <div className="text-5xl mb-4">💥</div>
                                <p className="font-pixel text-xs mc-text-glow-redstone mb-4">
                                    Processing failed
                                </p>
                                <PixelButton variant="redstone" onClick={resetJob}>
                                    🔄 Try Again
                                </PixelButton>
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Right Sidebar ── */}
                <aside className="w-80 flex flex-col gap-4">
                    {/* Job Info */}
                    <div className="mc-panel">
                        <div className="mc-panel-header">
                            <h2 className="font-pixel text-xs text-white">📦 JOB INFO</h2>
                        </div>
                        <div className="p-4 space-y-3">
                            {metadata ? (
                                <>
                                    <InfoRow label="File" value={metadata.original_filename} />
                                    <InfoRow
                                        label="Resolution"
                                        value={`${metadata.width}×${metadata.height}`}
                                    />
                                    <InfoRow label="FPS" value={`${metadata.fps}`} />
                                    <InfoRow
                                        label="Duration"
                                        value={`${metadata.duration.toFixed(1)}s`}
                                    />
                                    <InfoRow
                                        label="Frames"
                                        value={`${metadata.total_frames}`}
                                    />
                                </>
                            ) : (
                                <p className="font-pixel text-[10px] text-[var(--text-muted)]">
                                    Upload or select a forge to see details
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Processing Options */}
                    <div className="mc-panel">
                        <div className="mc-panel-header">
                            <h2 className="font-pixel text-xs text-white">⚙️ OPTIONS</h2>
                        </div>
                        <div className="p-4 space-y-4">
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={processOptions.useEnhancement}
                                    onChange={(e) =>
                                        setProcessOptions((p) => ({
                                            ...p,
                                            useEnhancement: e.target.checked,
                                        }))
                                    }
                                    className="w-5 h-5 accent-[var(--mc-emerald)]"
                                />
                                <span className="font-pixel text-[10px] text-[var(--text-primary)]">
                                    ✨ Real-ESRGAN Enhancement
                                </span>
                            </label>

                            <div>
                                <label className="font-pixel text-[10px] text-[var(--text-secondary)] block mb-2">
                                    CRF Quality ({processOptions.crf})
                                </label>
                                <input
                                    type="range"
                                    min={0}
                                    max={51}
                                    value={processOptions.crf}
                                    onChange={(e) =>
                                        setProcessOptions((p) => ({
                                            ...p,
                                            crf: parseInt(e.target.value),
                                        }))
                                    }
                                    className="w-full accent-[var(--mc-emerald)]"
                                />
                                <div className="flex justify-between font-pixel text-[8px] text-[var(--text-muted)]">
                                    <span>Lossless</span>
                                    <span>Lossy</span>
                                </div>
                            </div>

                            <div>
                                <label className="font-pixel text-[10px] text-[var(--text-secondary)] block mb-2">
                                    Codec
                                </label>
                                <select
                                    value={processOptions.codec}
                                    onChange={(e) =>
                                        setProcessOptions((p) => ({
                                            ...p,
                                            codec: e.target.value,
                                        }))
                                    }
                                    className="w-full p-2 bg-[var(--bg-glass)] border-2 border-[var(--border-pixel)] text-[var(--text-primary)] font-pixel text-[10px] rounded"
                                >
                                    <option value="libx264">H.264</option>
                                    <option value="libx265">H.265 (HEVC)</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="mc-panel p-4">
                        {(jobState === "uploaded" || jobState === "masking") && (
                            <PixelButton
                                variant="grass"
                                className="w-full"
                                onClick={startProcessing}
                                disabled={!maskDataUrl}
                            >
                                ⚔️ START PROCESSING
                            </PixelButton>
                        )}

                        {jobState === "completed" && outputUrl && (
                            <a href={outputUrl} download className="block">
                                <PixelButton variant="diamond" className="w-full">
                                    💎 DOWNLOAD
                                </PixelButton>
                            </a>
                        )}
                    </div>

                    {/* Pipeline Status */}
                    <div className="mc-panel">
                        <div className="mc-panel-header">
                            <h2 className="font-pixel text-xs text-white">🗺️ PIPELINE</h2>
                        </div>
                        <div className="p-4 space-y-2">
                            {[
                                { label: "Upload", step: 1 },
                                { label: "Extract Frames", step: 2 },
                                { label: "Generate Mask", step: 3 },
                                { label: "GPU Inpaint", step: 4 },
                                { label: "Temporal Smooth", step: 5 },
                                { label: "Enhance", step: 6 },
                                { label: "Rebuild Video", step: 7 },
                            ].map((s) => {
                                const currentStep = Math.ceil((progress / 100) * 7);
                                const done = (progress > 0 && s.step <= currentStep) || jobState === "completed";
                                const active = progress > 0 && s.step === currentStep && jobState !== "completed";
                                return (
                                    <div
                                        key={s.step}
                                        className={`flex items-center gap-3 px-3 py-2 rounded transition-all ${active
                                            ? "bg-[var(--mc-emerald)]/10 border border-[var(--mc-emerald)]/30"
                                            : ""
                                            }`}
                                    >
                                        <span
                                            className={`font-pixel text-[10px] ${done
                                                ? "mc-text-glow-green"
                                                : active
                                                    ? "mc-text-glow-gold"
                                                    : "text-[var(--text-muted)]"
                                                }`}
                                        >
                                            {done ? "✅" : active ? "⚡" : "⬜"}
                                        </span>
                                        <span
                                            className={`font-pixel text-[10px] ${done || active
                                                ? "text-[var(--text-primary)]"
                                                : "text-[var(--text-muted)]"
                                                }`}
                                        >
                                            {s.label}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </aside>
            </main>
            {/* ── Video Preview Modal ── */}
            {previewItem && (
                <VideoPreviewModal
                    isOpen={isPreviewOpen}
                    onClose={() => setIsPreviewOpen(false)}
                    videoUrl={`${API_URL}${previewItem.output_url}`}
                    filename={previewItem.filename}
                    onDownload={() => {
                        window.open(`${API_URL}/api/status/${previewItem.job_id}/download`, '_blank');
                    }}
                />
            )}
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between items-center">
            <span className="font-pixel text-[9px] text-[var(--text-muted)]">
                {label}
            </span>
            <span className="font-pixel text-[9px] text-[var(--text-primary)] truncate max-w-[140px]">
                {value}
            </span>
        </div>
    );
}

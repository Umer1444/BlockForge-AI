"use client";

import React, { useRef, useState, useEffect } from "react";
import { X, Play, Pause, Download, Volume2, VolumeX } from "lucide-react";
import PixelButton from "./PixelButton";

interface VideoPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    videoUrl: string;
    filename?: string;
    onDownload: () => void;
}

const VideoPreviewModal: React.FC<VideoPreviewModalProps> = ({
    isOpen,
    onClose,
    videoUrl,
    filename,
    onDownload
}) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [isMuted, setIsMuted] = useState(false);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);

    useEffect(() => {
        if (isOpen && videoUrl && videoRef.current) {
            videoRef.current.play().catch(() => {
                // Ignore interruption errors
                setIsPlaying(false);
            });
            setIsPlaying(true);
        }
    }, [isOpen, videoUrl]);

    if (!isOpen) return null;

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
                setIsPlaying(false);
            } else {
                videoRef.current.play().catch(() => { });
                setIsPlaying(true);
            }
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            const current = videoRef.current.currentTime;
            const total = videoRef.current.duration;
            setCurrentTime(current);
            if (!isNaN(total) && total > 0) {
                setProgress((current / total) * 100);
            }
        }
    };

    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            const d = videoRef.current.duration;
            if (!isNaN(d)) setDuration(d);
        }
    };

    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseFloat(e.target.value);
        if (isNaN(val)) return;

        const seekTime = (val / 100) * (duration || 0);
        if (videoRef.current && !isNaN(seekTime)) {
            videoRef.current.currentTime = seekTime;
            setProgress(val);
        }
    };

    const formatTime = (time: number) => {
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-300">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-4xl mc-panel bg-[#1a1a1a] shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden animate-in zoom-in duration-300">
                {/* Header */}
                <div className="mc-panel-header flex items-center justify-between px-4 py-2">
                    <h2 className="font-pixel text-xs text-white truncate max-w-[70%]">
                        FORGE PREVIEW: {filename || "RECONSTRUCTED_BLOCK.mp4"}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-[var(--text-muted)] hover:text-white transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Video Player Area */}
                <div className="relative group aspect-video bg-black flex items-center justify-center">
                    <video
                        ref={videoRef}
                        src={videoUrl}
                        className="w-full h-full"
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        onClick={togglePlay}
                        autoPlay
                    />

                    {/* Overlay Controls */}
                    <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                        {/* Progress Bar */}
                        <div className="mb-4 flex items-center gap-3">
                            <span className="font-pixel text-[8px] text-white w-10">
                                {formatTime(currentTime)}
                            </span>
                            <div className="flex-1 relative h-2 bg-[var(--mc-stone)] rounded overflow-hidden cursor-pointer">
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    value={progress}
                                    onChange={handleSeek}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                />
                                <div
                                    className="absolute inset-y-0 left-0 bg-[var(--mc-emerald)] shadow-[0_0_10px_rgba(0,255,0,0.5)] transition-all"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <span className="font-pixel text-[8px] text-white w-10">
                                {formatTime(duration)}
                            </span>
                        </div>

                        {/* Control Buttons */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <button onClick={togglePlay} className="text-white hover:text-[var(--mc-emerald)] transition-colors">
                                    {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 fill-current" />}
                                </button>
                                <button onClick={() => setIsMuted(!isMuted)} className="text-white hover:text-[var(--mc-gold)] transition-colors">
                                    {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                                </button>
                            </div>

                            <div className="flex gap-3">
                                <PixelButton variant="diamond" size="sm" onClick={onDownload}>
                                    <Download className="w-4 h-4 mr-2" />
                                    DOWNLOAD
                                </PixelButton>
                                <PixelButton variant="stone" size="sm" onClick={onClose}>
                                    CLOSE
                                </PixelButton>
                            </div>
                        </div>
                    </div>

                    {/* Big Center Play Button (only when paused) */}
                    {!isPlaying && (
                        <button
                            onClick={togglePlay}
                            className="absolute z-20 w-16 h-16 rounded-full bg-black/40 border-2 border-white/20 flex items-center justify-center hover:scale-110 transition-transform backdrop-blur-sm"
                        >
                            <Play className="w-8 h-8 text-white fill-white ml-1" />
                        </button>
                    )}
                </div>

                {/* Footer / Meta (XP Bar style) */}
                <div className="h-2 bg-[#2a2a2a] relative">
                    <div
                        className="absolute inset-y-0 left-0 bg-[var(--mc-emerald)] mc-xp-glow transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    />
                </div>
            </div>
        </div>
    );
};

export default VideoPreviewModal;

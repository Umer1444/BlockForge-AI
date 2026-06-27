"use client";

import React from "react";
import { Download, Play, CheckCircle2, Clock, AlertCircle, Trash2 } from "lucide-react";

export interface HistoryItem {
    id: string;
    job_id: string;
    filename?: string;
    state: string;
    progress: number;
    preview_url: string;
    thumbnail_url?: string;
    output_ready?: boolean;
    output_url?: string;
    created_at: number;
    width?: number;
    height?: number;
    resolution?: string;
    orientation?: string;
    fps?: number;
    duration?: number;
    file_size?: number;
}

interface HistoryCardProps {
    item: HistoryItem;
    onClick: (item: HistoryItem) => void;
    onDownload: (e: React.MouseEvent, item: HistoryItem) => void;
    onDelete?: (e: React.MouseEvent, item: HistoryItem) => void;
    isActive?: boolean;
    apiUrl: string;
}

const HistoryCard: React.FC<HistoryCardProps> = ({ item, onClick, onDownload, onDelete, isActive, apiUrl }) => {
    const formattedSize = item.file_size
        ? (item.file_size / (1024 * 1024)).toFixed(1) + " MB"
        : "Unknown size";

    const formattedDate = new Date(item.created_at * 1000).toLocaleDateString();

    const getStatusIcon = () => {
        switch (item.state.toLowerCase()) {
            case "completed": return <CheckCircle2 className="w-3 h-3 text-[var(--mc-emerald)]" />;
            case "processing": return <Clock className="w-3 h-3 text-[var(--mc-gold)] animate-pulse" />;
            case "failed": return <AlertCircle className="w-3 h-3 text-[var(--mc-redstone)]" />;
            default: return <Clock className="w-3 h-3 text-[var(--text-muted)]" />;
        }
    };

    const getOrientationBadge = () => {
        if (!item.orientation) return null;
        const colors: Record<string, string> = {
            landscape: "bg-blue-500/20 text-blue-400 border-blue-500/50",
            portrait: "bg-purple-500/20 text-purple-400 border-purple-500/50",
            square: "bg-orange-500/20 text-orange-400 border-orange-500/50"
        };
        return (
            <span className={`px-1.5 py-0.5 rounded border text-[6px] uppercase font-pixel ${colors[item.orientation] || ""}`}>
                {item.orientation}
            </span>
        );
    };

    return (
        <div
            onClick={() => onClick(item)}
            className={`group relative mc-panel p-2 cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_15px_rgba(0,255,0,0.1)] ${isActive ? "border-[var(--mc-emerald)] shadow-[0_0_10px_rgba(0,255,0,0.2)]" : "border-[var(--border-pixel)]"
                }`}
        >
            {/* Thumbnail Preview */}
            <div className="aspect-video mc-panel overflow-hidden mb-2 bg-[#1a1a1a] relative">
                <img
                    src={`${apiUrl}${item.thumbnail_url || item.preview_url}`}
                    alt={item.filename || "Video preview"}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />

                {/* Overlay Play Hint */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="w-8 h-8 rounded-full bg-[var(--mc-emerald)]/20 border border-[var(--mc-emerald)] flex items-center justify-center">
                        <Play className="w-4 h-4 text-[var(--mc-emerald)] fill-[var(--mc-emerald)]" />
                    </div>
                </div>

                {/* Status Badge */}
                <div className="absolute top-1 right-1 px-1 py-0.5 bg-black/60 rounded flex items-center gap-1">
                    {getStatusIcon()}
                </div>
            </div>

            {/* Content */}
            <div className="space-y-1">
                <div className="font-pixel text-[8px] truncate text-white group-hover:text-[var(--mc-emerald)] transition-colors">
                    {item.filename || "Unnamed Forge"}
                </div>

                <div className="flex flex-wrap gap-1 items-center">
                    {getOrientationBadge()}
                    <span className="font-pixel text-[6px] text-[var(--text-muted)]">
                        {item.resolution || "Unknown res"}
                    </span>
                </div>

                <div className="flex justify-between items-center pt-1 border-t border-[var(--border-pixel)]/30">
                    <div className="flex flex-col">
                        <span className="font-pixel text-[6px] text-[var(--text-muted)]">
                            {formattedSize} • {item.duration ? `${item.duration.toFixed(1)}s` : "0s"}
                        </span>
                        <span className="font-pixel text-[5px] text-[var(--text-muted)]/60">
                            {formattedDate}
                        </span>
                    </div>

                    <div className="flex gap-1">
                        {onDelete && (
                            <button
                                onClick={(e) => onDelete(e, item)}
                                className="p-1.5 rounded mc-panel bg-[var(--mc-stone)] hover:bg-[var(--mc-redstone)] transition-colors group/del"
                                title="Delete from Server"
                            >
                                <Trash2 className="w-3 h-3 text-white group-hover/del:scale-110 transition-transform" />
                            </button>
                        )}
                        {item.state === "completed" && item.output_url && (
                            <button
                                onClick={(e) => onDownload(e, item)}
                                className="p-1.5 rounded mc-panel bg-[var(--mc-stone)] hover:bg-[var(--mc-emerald)] transition-colors group/btn"
                                title="Download Video"
                            >
                                <Download className="w-3 h-3 text-white group-hover/btn:scale-110 transition-transform" />
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Hover Glow Effect */}
            <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow-[inset_0_0_20px_rgba(0,255,0,0.05)]" />
        </div>
    );
};

export default HistoryCard;

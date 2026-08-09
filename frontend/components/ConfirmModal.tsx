"use client";

import React from "react";
import { AlertTriangle, X } from "lucide-react";
import PixelButton from "./PixelButton";

interface ConfirmModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    onConfirm: () => void;
    onCancel: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
    isOpen,
    title,
    message,
    confirmText = "CONFIRM",
    cancelText = "CANCEL",
    onConfirm,
    onCancel,
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                onClick={onCancel}
            />

            {/* Modal Box */}
            <div className="relative w-full max-w-md mc-panel bg-[#1a1a1a] p-6 shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden animate-in zoom-in duration-200 border-2 border-[var(--mc-redstone)]">
                <button
                    onClick={onCancel}
                    className="absolute top-3 right-3 text-[var(--text-muted)] hover:text-white transition-colors"
                    aria-label="Close confirmation dialog"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded bg-[var(--mc-redstone)]/20 border border-[var(--mc-redstone)] text-[var(--mc-redstone)]">
                        <AlertTriangle className="w-6 h-6 animate-pulse" />
                    </div>
                    <h2 className="font-pixel text-xs text-white uppercase tracking-wide">
                        {title}
                    </h2>
                </div>

                <p className="font-pixel text-[10px] text-[var(--text-secondary)] leading-relaxed mb-6">
                    {message}
                </p>

                <div className="flex gap-3 justify-end pt-2 border-t border-[var(--border-pixel)]/40">
                    <PixelButton variant="stone" size="sm" onClick={onCancel}>
                        {cancelText}
                    </PixelButton>
                    <PixelButton variant="redstone" size="sm" onClick={onConfirm}>
                        {confirmText}
                    </PixelButton>
                </div>
            </div>
        </div>
    );
};

export default ConfirmModal;

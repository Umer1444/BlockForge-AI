"use client";

import React, { useEffect } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

export type ToastType = "error" | "success" | "info";

interface ToastProps {
    message: string | null;
    type?: ToastType;
    onClose: () => void;
    duration?: number;
}

const Toast: React.FC<ToastProps> = ({
    message,
    type = "error",
    onClose,
    duration = 4000,
}) => {
    useEffect(() => {
        if (!message) return;
        const timer = setTimeout(() => {
            onClose();
        }, duration);
        return () => clearTimeout(timer);
    }, [message, duration, onClose]);

    if (!message) return null;

    const styles = {
        error: "bg-[#2a1414] border-[var(--mc-redstone)] text-red-200 shadow-[0_0_15px_rgba(255,0,0,0.3)]",
        success: "bg-[#142a18] border-[var(--mc-emerald)] text-emerald-200 shadow-[0_0_15px_rgba(0,255,0,0.3)]",
        info: "bg-[#141f2a] border-[var(--mc-diamond)] text-blue-200 shadow-[0_0_15px_rgba(0,200,255,0.3)]",
    }[type];

    const Icon = {
        error: AlertCircle,
        success: CheckCircle2,
        info: Info,
    }[type];

    return (
        <div className="fixed top-6 right-6 z-[120] animate-in slide-in-from-top-5 duration-300">
            <div
                role="alert"
                className={`mc-panel flex items-center gap-3 px-4 py-3 border-2 max-w-sm rounded ${styles}`}
            >
                <Icon className="w-5 h-5 shrink-0 animate-bounce" />
                <span className="font-pixel text-[10px] flex-1 leading-snug">
                    {message}
                </span>
                <button
                    onClick={onClose}
                    className="p-1 hover:opacity-80 transition-opacity"
                    aria-label="Dismiss notification"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
};

export default Toast;

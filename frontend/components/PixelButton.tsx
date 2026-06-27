"use client";

import React from "react";

interface PixelButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "grass" | "stone" | "diamond" | "redstone" | "gold";
    size?: "sm" | "md" | "lg";
    children: React.ReactNode;
}

export default function PixelButton({
    variant = "grass",
    size = "md",
    children,
    className = "",
    disabled,
    ...props
}: PixelButtonProps) {
    const sizeClasses = {
        sm: "text-[9px] px-3 py-2",
        md: "text-xs px-5 py-3",
        lg: "text-sm px-8 py-4",
    };

    return (
        <button
            className={`mc-btn mc-btn-${variant} ${sizeClasses[size]} ${className} ${disabled ? "opacity-50 cursor-not-allowed" : ""
                }`}
            disabled={disabled}
            {...props}
        >
            {children}
        </button>
    );
}

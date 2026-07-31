import { CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { LucideIcon } from "lucide-react";

export interface StatusConfig {
    icon: LucideIcon;
    className: string;
}

export const STATUS_CONFIG: Record<string, StatusConfig> = {
    completed: {
        icon: CheckCircle2,
        className: "text-[var(--mc-emerald)]",
    },
    processing: {
        icon: Clock,
        className: "text-[var(--mc-gold)] animate-pulse",
    },
    failed: {
        icon: AlertCircle,
        className: "text-[var(--mc-redstone)]",
    },
};

export const DEFAULT_STATUS: StatusConfig = {
    icon: Clock,
    className: "text-[var(--text-muted)]",
};
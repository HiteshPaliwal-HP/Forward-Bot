import { CheckCircle2, Circle, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StatusPillStatus } from "@/types/ui";

interface StatusPillProps {
  status: StatusPillStatus;
  className?: string;
}

const CONFIG = {
  active: {
    classes: "bg-success-bg border-success-border text-success-foreground",
    icon: CheckCircle2,
    label: "Active"
  },
  inactive: {
    classes: "bg-muted-bg border-border text-muted-foreground",
    icon: Circle,
    label: "Inactive"
  },
  error: {
    classes: "bg-error-bg border-error-border text-error",
    icon: AlertCircle,
    label: "Error"
  },
  stale: {
    classes: "bg-warning-bg border-warning-border text-warning-foreground",
    icon: Clock,
    label: "Stale"
  }
};

export function StatusPill({ status, className }: StatusPillProps) {
  const config = CONFIG[status];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold select-none border capitalize",
        config.classes,
        className
      )}
    >
      <Icon className="w-3 h-3 flex-shrink-0" />
      <span>{config.label}</span>
    </span>
  );
}

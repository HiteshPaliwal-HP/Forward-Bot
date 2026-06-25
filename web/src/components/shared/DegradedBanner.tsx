import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface DegradedBannerProps {
  message: string;
  onReconnect: () => void;
  isLoading?: boolean;
}

export function DegradedBanner({ message, onReconnect, isLoading = false }: DegradedBannerProps) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="w-full bg-degraded-bg border-b border-degraded-border text-degraded-foreground py-3 px-4 flex flex-col sm:flex-row items-center justify-between gap-3 select-none"
    >
      <div className="flex items-center gap-2">
        <AlertCircle className="w-5 h-5 flex-shrink-0 text-error animate-pulse" />
        <span className="text-sm font-semibold tracking-tight leading-normal">{message}</span>
      </div>

      <button
        onClick={onReconnect}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold border cursor-pointer select-none transition-all duration-300 bg-error text-white border-transparent hover:bg-red-700 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 disabled:hover:bg-error"
      >
        <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
        <span>{isLoading ? "Reconnecting..." : "Reconnect"}</span>
      </button>
    </div>
  );
}

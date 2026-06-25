import { Link } from "react-router-dom";
import { AlertTriangle, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActivationBannerProps {
  isActive: boolean;
  onActivate: () => void;
  isFirstRun?: boolean;
  isLoading?: boolean;
  className?: string;
}

export function ActivationBanner({
  isActive,
  onActivate,
  isFirstRun = false,
  isLoading = false,
  className
}: ActivationBannerProps) {
  if (isFirstRun) {
    return (
      <div 
        className={cn(
          "w-full bg-warning-bg border border-warning-border rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 text-warning-foreground shadow-2xs select-none",
          className
        )}
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-bold text-sm">Welcome to Forward Bot!</h3>
            <p className="text-xs mt-1 leading-normal opacity-90 font-medium">
              There are no forwarding rules configured yet. Create a forwarding rule to begin routing messages between Telegram channels.
            </p>
          </div>
        </div>
        <Link 
          to="/forwards/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-warning-foreground text-white rounded-md text-xs font-bold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-3xs self-start md:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create your first rule</span>
        </Link>
      </div>
    );
  }

  if (isActive) {
    return null;
  }

  return (
    <div 
      className={cn(
        "w-full bg-warning-bg border border-warning-border rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-warning-foreground shadow-2xs select-none",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
        <span className="text-sm font-bold tracking-tight leading-normal">
          This forward is inactive. Activate to begin processing.
        </span>
      </div>
      <button
        onClick={onActivate}
        disabled={isLoading}
        className="px-4 py-1.5 bg-warning-foreground text-white rounded-md text-xs font-bold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-3xs self-start sm:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
      >
        {isLoading ? "Activating..." : "Activate"}
      </button>
    </div>
  );
}

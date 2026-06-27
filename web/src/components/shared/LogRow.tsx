import React, { useState } from "react";
import { 
  ArrowUpRight, 
  CircleSlash, 
  AlertTriangle, 
  Ban, 
  Clock, 
  Pencil, 
  Trash2, 
  CornerDownRight, 
  Info,
  Copy,
  Check,
  Filter
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { LogEntry } from "@/types/ui";
import { Tooltip } from "./Tooltip";

type LogRowVariant = 
  | "forwarded"
  | "filter_blocked"
  | "telegram_rejected"
  | "destination_unreachable"
  | "flood_wait"
  | "edit_propagated"
  | "delete_propagated"
  | "reply_orphaned"
  | "default";

const VARIANT_MAP: Record<string, LogRowVariant> = {
  forward_succeeded: "forwarded",
  edit_propagated: "edit_propagated",
  delete_propagated: "delete_propagated",
  
  pipeline_blocked: "filter_blocked",
  outside_time_window: "filter_blocked",
  sampled_out: "filter_blocked",
  media_type_filtered: "filter_blocked",
  blocked_keyword: "filter_blocked",
  no_allow_keyword_matched: "filter_blocked",
  empty_after_processing: "filter_blocked",
  unsupported_media_type: "filter_blocked",
  
  forward_failed: "telegram_rejected",
  media_replacement_failed: "telegram_rejected",
  telegram_session_invalidated: "telegram_rejected",
  
  flood_wait: "flood_wait",
  reply_parent_not_found: "reply_orphaned",
  reply_target_missing: "reply_orphaned",
};

const CONFIG_MAP: Record<LogRowVariant, {
  stripeClass: string;
  icon: React.ComponentType<any>;
  iconClass: string;
  labelClass?: string;
}> = {
  forwarded: {
    stripeClass: "border-success",
    icon: ArrowUpRight,
    iconClass: "text-success",
  },
  filter_blocked: {
    stripeClass: "border-muted",
    icon: CircleSlash,
    iconClass: "text-muted-foreground",
  },
  telegram_rejected: {
    stripeClass: "border-error",
    icon: AlertTriangle,
    iconClass: "text-error",
  },
  destination_unreachable: {
    stripeClass: "border-error",
    icon: Ban,
    iconClass: "text-error",
  },
  flood_wait: {
    stripeClass: "border-warning-border",
    icon: Clock,
    iconClass: "text-warning-foreground",
  },
  edit_propagated: {
    stripeClass: "border-success",
    icon: Pencil,
    iconClass: "text-success",
  },
  delete_propagated: {
    stripeClass: "border-success",
    icon: Trash2,
    iconClass: "text-success",
  },
  reply_orphaned: {
    stripeClass: "border-warning-border",
    icon: CornerDownRight,
    iconClass: "text-warning-foreground",
    labelClass: "line-through opacity-70 text-warning-foreground/70",
  },
  default: {
    stripeClass: "border-border",
    icon: Info,
    iconClass: "text-muted-foreground",
  },
};

const formatEventLabel = (event: string) => {
  return event
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const formatTimestamp = (ts: string) => {
  try {
    const date = new Date(ts);
    if (isNaN(date.getTime())) return ts;
    return date.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });
  } catch (e) {
    return ts;
  }
};

const getPayloadPreview = (entry: LogEntry) => {
  if (entry.payload && typeof entry.payload === "object") {
    return JSON.stringify(entry.payload);
  }
  const { event, level, timestamp, correlation_id, rule_id, ...rest } = entry;
  if (Object.keys(rest).length === 0) return "";
  return JSON.stringify(rest);
};

interface LogRowProps {
  entry: LogEntry;
  onFilterByCorrelationId?: (id: string) => void;
}

export function LogRow({ entry, onFilterByCorrelationId }: LogRowProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const variant = VARIANT_MAP[entry.event] || "default";
  const config = CONFIG_MAP[variant];
  const Icon = config.icon;

  const handleRowClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest("button") || target.closest("a")) {
      return;
    }
    setIsOpen(!isOpen);
  };

  const handleCopyCorrelation = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (entry.correlation_id) {
      navigator.clipboard.writeText(entry.correlation_id);
      setCopied(true);
      toast.success("Correlation ID copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const payloadPreview = getPayloadPreview(entry);

  return (
    <div 
      className={cn(
        "border border-border border-l-4 rounded-md overflow-hidden bg-card hover:bg-muted/15 transition-all duration-200 shadow-2xs select-none",
        config.stripeClass,
        isOpen && "shadow-xs"
      )}
    >
      <div 
        role="button"
        tabIndex={0}
        onClick={handleRowClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleRowClick(e);
          }
        }}
        className="flex items-center justify-between p-3.5 gap-4 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <Icon className={cn("w-5 h-5 flex-shrink-0", config.iconClass)} />
          <span className={cn("text-sm font-bold text-foreground truncate max-w-[180px] sm:max-w-[240px]", config.labelClass)}>
            {formatEventLabel(entry.event)}
          </span>
          {payloadPreview && (
            <span className="text-xs font-mono text-muted-foreground truncate max-w-sm sm:max-w-md md:max-w-lg hidden sm:inline select-text">
              {payloadPreview}
            </span>
          )}
        </div>

        <div className="flex-shrink-0 flex items-center">
          <Tooltip content={new Date(entry.timestamp).toLocaleString()}>
            <span className="text-xs text-muted-foreground font-medium tabular-nums">
              {formatTimestamp(entry.timestamp)}
            </span>
          </Tooltip>
        </div>
      </div>

      <div 
        className={cn(
          "grid transition-all duration-300 ease-in-out border-border bg-muted/10",
          isOpen ? "grid-rows-[1fr] border-t" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <div className="p-4 flex flex-col gap-3.5 select-text">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Level:</span>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full font-semibold border capitalize",
                  entry.level === "debug" && "bg-muted-bg border-border text-muted-foreground",
                  entry.level === "info" && "bg-success-bg border-success-border text-success-foreground",
                  (entry.level === "warning" || entry.level === "error" || entry.level === "critical") && "bg-error-bg border-error-border text-error"
                )}>
                  {entry.level}
                </span>
              </div>
              
              <div className="flex items-center gap-3">
                {entry.correlation_id && (
                  <button
                    onClick={handleCopyCorrelation}
                    className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-card hover:bg-muted border border-border rounded-md text-muted-foreground hover:text-foreground transition-all cursor-pointer shadow-3xs"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? "Copied" : "Copy Correlation ID"}</span>
                  </button>
                )}
                {entry.correlation_id && onFilterByCorrelationId && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onFilterByCorrelationId(entry.correlation_id!);
                    }}
                    className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-card hover:bg-muted border border-border rounded-md text-muted-foreground hover:text-foreground transition-all cursor-pointer shadow-3xs"
                  >
                    <Filter className="w-3.5 h-3.5 text-primary" />
                    <span>Filter by this ID</span>
                  </button>
                )}
                {entry.rule_id && (
                  <Link
                    to={`/forwards?id=${entry.rule_id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs text-primary hover:underline flex items-center gap-1 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span>Jump to rule →</span>
                  </Link>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-muted-foreground">Payload Details:</span>
              <pre className="font-mono text-xs text-foreground p-3 bg-card border border-border rounded-md overflow-x-auto max-w-full shadow-3xs font-mono">
                {JSON.stringify(entry, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useRef, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { 
  Play, 
  Pause, 
  ArrowDown, 
  Filter, 
  X, 
  AlertCircle,
  Activity
} from "lucide-react";

import { logsApi } from "@/api/logs";
import { healthApi } from "@/api/health";
import { useSseLog } from "@/hooks/useSseLog";
import { LogRow, DegradedBanner } from "@/components/shared";
import type { LogEntry } from "@/types/ui";

const SEVERITIES = ["info", "warning", "error", "success"] as const;
type Severity = typeof SEVERITIES[number];

const getDisplaySeverity = (entry: LogEntry): Severity => {
  const successEvents = ["forward_succeeded", "edit_propagated", "delete_propagated", "mapping_sweep_completed"];
  if (successEvents.includes(entry.event)) return "success";
  if (entry.level === "critical" || entry.level === "error") return "error";
  if (entry.level === "warning") return "warning";
  return "info";
};

export default function Logs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const [sseForceDisabled, setSseForceDisabled] = useState(false);
  const [isReconnectLoading, setIsReconnectLoading] = useState(false);

  // Active filters from URL
  const activeSeverities = useMemo(() => searchParams.getAll("severity"), [searchParams]);
  const activeCorrelationId = searchParams.get("correlation_id") ?? "";

  // 1. Fetch historical batch (last 200 entries)
  const { 
    data: historicalData, 
    isLoading, 
    isError: isHistoricalError,
    refetch: refetchHistorical
  } = useQuery({
    queryKey: ["logs", "recent"],
    queryFn: () => logsApi.fetchRecent(200),
    staleTime: 0,
  });

  const historicalEntries = useMemo(() => historicalData?.items ?? [], [historicalData]);

  // Determine starting cutoff timestamp from historical entries
  const startAfterTimestamp = useMemo(() => {
    if (historicalEntries.length === 0) return undefined;
    return historicalEntries[historicalEntries.length - 1].timestamp;
  }, [historicalEntries]);

  // 2. Open SSE stream connection
  const { 
    entries: sseEntries, 
    isConnected, 
    isError: isSseError 
  } = useSseLog({
    enabled: !isLoading && !isHistoricalError && !sseForceDisabled,
    startAfterTimestamp,
  });

  // 3. Merge and deduplicate entries chronologically
  const allEntries = useMemo(() => {
    const merged = [...historicalEntries, ...sseEntries];
    const seen = new Set<string>();
    const deduped: LogEntry[] = [];
    
    for (const entry of merged) {
      const key = `${entry.timestamp}_${entry.event}_${entry.correlation_id ?? ""}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(entry);
      }
    }

    // Sort oldest at top, newest at bottom
    return deduped.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [historicalEntries, sseEntries]);

  // 4. Client-side filtering
  const filteredEntries = useMemo(() => {
    return allEntries.filter((entry) => {
      const displaySeverity = getDisplaySeverity(entry);
      const severityMatch = activeSeverities.length === 0 || activeSeverities.includes(displaySeverity);
      const correlationMatch = !activeCorrelationId || entry.correlation_id === activeCorrelationId;
      return severityMatch && correlationMatch;
    });
  }, [allEntries, activeSeverities, activeCorrelationId]);

  // Extract rule_id from matching correlation entries for routing helper link
  const activeRuleId = useMemo(() => {
    if (!activeCorrelationId) return null;
    const match = allEntries.find(
      (entry) => entry.correlation_id === activeCorrelationId && entry.rule_id
    );
    return match?.rule_id ?? null;
  }, [allEntries, activeCorrelationId]);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  // Scroll handler to detect manual scroll-up
  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    if (!isNearBottom && isAutoScroll) {
      setIsAutoScroll(false);
    } else if (isNearBottom && !isAutoScroll) {
      setIsAutoScroll(true);
    }
  };

  // Auto-scroll when new log entries arrive
  useEffect(() => {
    if (isAutoScroll) {
      scrollToBottom();
    }
  }, [allEntries, isAutoScroll]);

  // SSE reconnect mechanism
  const handleReconnect = async () => {
    setIsReconnectLoading(true);
    try {
      // Validate Telegram auth/status before reconnecting
      await healthApi.fetchTelegramStatus();
      // Force cycle the EventSource
      setSseForceDisabled(true);
      setTimeout(() => {
        setSseForceDisabled(false);
        toast.success("Reconnecting live log stream...");
      }, 100);
    } catch {
      toast.error("Could not reach backend health check. Reconnect failed.");
    } finally {
      setIsReconnectLoading(false);
    }
  };

  // Severity toggle filter
  const handleToggleSeverity = (severity: Severity) => {
    const current = new URLSearchParams(searchParams);
    const existing = current.getAll("severity");
    if (existing.includes(severity)) {
      const next = existing.filter((s) => s !== severity);
      current.delete("severity");
      next.forEach((s) => current.append("severity", s));
    } else {
      current.append("severity", severity);
    }
    setSearchParams(current);
  };

  // Correlation ID change
  const handleCorrelationIdChange = (id: string) => {
    const current = new URLSearchParams(searchParams);
    if (id) {
      current.set("correlation_id", id);
    } else {
      current.delete("correlation_id");
    }
    setSearchParams(current);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setSearchParams({});
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] gap-4 select-none">
      {/* Header section */}
      <div className="flex items-center justify-between flex-wrap gap-4 px-1">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">System Logs</h1>
            {!isLoading && (
              <div className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border transition-all ${
                isConnected 
                  ? "bg-success-bg border-success-border text-success-foreground" 
                  : "bg-error-bg border-error-border text-error"
              }`}>
                <Activity className={`w-3.5 h-3.5 ${isConnected ? "animate-pulse" : ""}`} />
                <span>{isConnected ? "Live Feed" : "Disconnected"}</span>
              </div>
            )}
          </div>
          <p className="text-sm text-muted-foreground font-medium">
            Real-time feed of message events, processing filters, and forwarding status.
          </p>
        </div>
      </div>

      {/* Filter and controls bar */}
      <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-3 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Severity Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider mr-2">Severity</span>
            {SEVERITIES.map((severity) => {
              const isActive = activeSeverities.includes(severity);
              return (
                <button
                  key={severity}
                  onClick={() => handleToggleSeverity(severity)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-full capitalize border transition-all cursor-pointer ${
                    isActive
                      ? severity === "info"
                        ? "bg-muted border-muted text-foreground"
                        : severity === "warning"
                        ? "bg-warning-bg border-warning-border text-warning-foreground"
                        : severity === "error"
                        ? "bg-error-bg border-error-border text-error"
                        : "bg-success-bg border-success-border text-success-foreground"
                      : "bg-card border-border hover:bg-muted-bg text-muted-foreground"
                  }`}
                >
                  {severity}
                </button>
              );
            })}
          </div>

          {/* Correlation ID search */}
          <div className="flex items-center gap-2 w-full sm:w-auto min-w-[280px]">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider shrink-0">Trace ID</span>
            <div className="relative w-full">
              <input
                type="text"
                placeholder="correlation-id"
                value={activeCorrelationId}
                onChange={(e) => handleCorrelationIdChange(e.target.value)}
                className="w-full bg-muted-bg border border-border hover:border-muted-foreground/30 focus:border-primary focus:ring-1 focus:ring-ring rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none transition-all placeholder:text-muted-foreground"
              />
              {activeCorrelationId && (
                <button
                  onClick={() => handleCorrelationIdChange("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Clear Filters / Trace Helpers */}
        {(activeSeverities.length > 0 || activeCorrelationId) && (
          <div className="flex flex-wrap items-center justify-between border-t border-border pt-3 mt-1 flex-row">
            <div className="flex items-center gap-2">
              <button
                onClick={handleClearFilters}
                className="inline-flex items-center gap-1 text-xs text-error font-bold hover:underline cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
                <span>Clear active filters</span>
              </button>
              {activeCorrelationId && activeRuleId && (
                <>
                  <span className="text-muted-foreground text-xs mx-1">|</span>
                  <Link
                    to={`/forwards/${activeRuleId}/edit`}
                    className="inline-flex items-center gap-1 text-xs text-primary font-bold hover:underline cursor-pointer"
                  >
                    <span>Jump to forwarding rule →</span>
                  </Link>
                </>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              Showing {filteredEntries.length} of {allEntries.length} buffered log events
            </span>
          </div>
        )}
      </div>

      {/* SSE Connection error banner */}
      {isSseError && (
        <DegradedBanner
          message="Live log stream disconnected — reconnecting…"
          onReconnect={handleReconnect}
          isLoading={isReconnectLoading}
        />
      )}

      {/* Main logs display listing */}
      <div className="flex-1 min-h-0 bg-card border border-border rounded-xl relative shadow-2xs overflow-hidden">
        {isLoading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-border border-t-primary animate-spin" />
            <span className="text-xs text-muted-foreground font-semibold">Loading system logs...</span>
          </div>
        ) : isHistoricalError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center gap-3">
            <AlertCircle className="w-10 h-10 text-error animate-bounce" />
            <h3 className="text-sm font-bold text-foreground">Failed to Load Logs</h3>
            <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
              Could not retrieve the recent log events from the server. Check backend connectivity.
            </p>
            <button
              onClick={() => refetchHistorical()}
              className="px-3.5 py-1.5 bg-primary text-white hover:opacity-90 font-bold rounded-lg text-xs shadow-3xs cursor-pointer"
            >
              Retry Load
            </button>
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
            <Filter className="w-10 h-10 text-muted mb-2.5 opacity-60" />
            <h3 className="text-sm font-bold text-foreground">No Logs Found</h3>
            <p className="text-xs text-muted-foreground max-w-xs leading-relaxed mt-1">
              {activeSeverities.length > 0 || activeCorrelationId
                ? "No log entries match the current filters. Adjust severities or correlation ID."
                : "No activities registered. Events will appear here as message operations run."}
            </p>
            {(activeSeverities.length > 0 || activeCorrelationId) && (
              <button
                onClick={handleClearFilters}
                className="mt-3.5 text-xs text-primary font-bold hover:underline cursor-pointer"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div
              ref={scrollRef}
              onScroll={handleScroll}
              className="w-full h-full overflow-y-auto p-4 flex flex-col gap-3"
            >
              {filteredEntries.map((entry, index) => (
                <LogRow
                  key={`${entry.timestamp}_${entry.event}_${index}`}
                  entry={entry}
                  onFilterByCorrelationId={handleCorrelationIdChange}
                />
              ))}
            </div>

            {/* Floating Auto-scroll indicator / Jump to bottom */}
            {!isAutoScroll && (
              <button
                onClick={() => {
                  setIsAutoScroll(true);
                  scrollToBottom();
                }}
                className="absolute bottom-4 right-4 flex items-center gap-1.5 px-3 py-2 bg-primary hover:opacity-95 text-primary-foreground text-xs font-bold rounded-full shadow-lg transition-all animate-bounce cursor-pointer select-none border border-transparent"
              >
                <ArrowDown className="w-3.5 h-3.5" />
                <span>Jump to latest</span>
              </button>
            )}
          </>
        )}
      </div>

      {/* Footer Controls */}
      {!isLoading && !isHistoricalError && (
        <div className="flex items-center justify-between px-1 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAutoScroll(!isAutoScroll)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-card hover:bg-muted border border-border text-muted-foreground hover:text-foreground text-xs font-bold rounded-lg transition-all cursor-pointer"
            >
              {isAutoScroll ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{isAutoScroll ? "Pause Scroll" : "Auto Scroll"}</span>
            </button>
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
              {isAutoScroll ? "Tail Mode Enabled" : "Tail Mode Paused"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
            <span>Buffer limit: 1000 items</span>
          </div>
        </div>
      )}
    </div>
  );
}

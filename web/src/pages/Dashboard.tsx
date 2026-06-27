import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { healthApi } from "@/api/health";
import { statsApi } from "@/api/stats";
import { logsApi } from "@/api/logs";
import { rulesApi } from "@/api/rules";
import { queryKeys } from "@/lib/queryKeys";
import { LogRow, ActivationBanner } from "@/components/shared";
import { FirstRunWizard } from "@/components/FirstRunWizard";
import { 
  Activity, 
  Server, 
  Send, 
  AlertOctagon, 
  ShieldAlert, 
  ArrowRight, 
  RefreshCw,
  Sliders,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const [wizardOpen, setWizardOpen] = useState(false);

  // 1. Telegram Status Query (staleTime 30s)
  const { 
    data: telegramData, 
    isLoading: isTelegramLoading, 
    isError: isTelegramError,
    refetch: refetchTelegram 
  } = useQuery({
    queryKey: queryKeys.health.telegram(),
    queryFn: healthApi.fetchTelegramStatus,
    staleTime: 30_000,
  });

  // 2. MongoDB Status Query (staleTime 30s)
  const { 
    data: cacheData, 
    isLoading: isCacheLoading, 
    isError: isCacheError,
    refetch: refetchCache 
  } = useQuery({
    queryKey: queryKeys.health.cache(),
    queryFn: healthApi.fetchCacheStatus,
    staleTime: 30_000,
  });

  // 3. Stats Summary Query (staleTime 60s)
  const { 
    data: statsData, 
    isLoading: isStatsLoading, 
    isError: isStatsError,
    refetch: refetchStats 
  } = useQuery({
    queryKey: queryKeys.stats.summary(),
    queryFn: statsApi.fetchSummary,
    staleTime: 60_000,
  });

  // 4. Recent Logs Query (staleTime 10s)
  const { 
    data: logsData, 
    isLoading: isLogsLoading, 
    isError: isLogsError,
    refetch: refetchLogs 
  } = useQuery({
    queryKey: queryKeys.logs.recent(),
    queryFn: () => logsApi.fetchRecent(20),
    staleTime: 10_000,
  });

  // 5. Total Rules Query for First Run Detection (staleTime 30s)
  const { 
    data: rulesData, 
    isLoading: isRulesLoading,
    isError: isRulesError,
    refetch: refetchRules
  } = useQuery({
    queryKey: [...queryKeys.rules.list(), { page_size: 1 }],
    queryFn: () => rulesApi.fetchRules({ page_size: 1 }),
    staleTime: 30_000,
  });

  const isFirstRun = !isRulesLoading && !isRulesError && rulesData?.total === 0;

  useEffect(() => {
    if (isFirstRun) {
      const dismissed = localStorage.getItem("fb-first-run-dismissed") === "true";
      if (!dismissed) {
        setWizardOpen(true);
      }
    }
  }, [isFirstRun]);

  const handleDismissWizard = () => {
    localStorage.setItem("fb-first-run-dismissed", "true");
    setWizardOpen(false);
  };

  // Telegram helper status
  const telegramStatus = telegramData?.telegram || "disconnected";
  const isMongoDown = cacheData?.mongodb !== "up";

  return (
    <div className="flex flex-col gap-5 select-none">
      {/* Page Header */}
      <div className="flex flex-col gap-0.5">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-xs text-muted-foreground font-medium">
          Monitor bot operation status, key delivery statistics, and recent system activities.
        </p>
      </div>
 
      {/* Conditionally render ActivationBanner if rules list is empty */}
      {!isRulesLoading && !isRulesError && isFirstRun && (
        <ActivationBanner 
          isActive={false} 
          onActivate={() => {}} 
          isFirstRun={true} 
        />
      )}
 
      {/* Status Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Telegram Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium relative overflow-hidden flex flex-col justify-between min-h-[130px] hover:border-muted/80 transition-all duration-200">
          {isTelegramLoading ? (
            <div className="flex flex-col gap-3.5 w-full animate-pulse">
              <div className="h-3 bg-muted rounded w-1/3"></div>
              <div className="h-6 bg-muted rounded w-2/3"></div>
              <div className="h-3 bg-muted rounded w-1/2"></div>
            </div>
          ) : isTelegramError ? (
            <div className="flex flex-col justify-between h-full w-full">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span className="text-xs font-bold">Connection Failed</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
                Could not retrieve Telegram connectivity status.
              </p>
              <button 
                onClick={() => refetchTelegram()}
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline cursor-pointer select-none"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry connection check</span>
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Telegram Link</span>
                <Activity className={cn(
                  "w-4 h-4",
                  telegramStatus === "connected" && "text-emerald-500",
                  telegramStatus === "reconnecting" && "text-amber-500",
                  telegramStatus === "disconnected" && "text-red-500"
                )} />
              </div>
              <div className="mt-2.5 flex items-baseline gap-2">
                <h3 className={cn(
                  "text-lg font-bold tracking-tight capitalize",
                  telegramStatus === "connected" && "text-foreground",
                  telegramStatus === "reconnecting" && "text-amber-500",
                  telegramStatus === "disconnected" && "text-red-500"
                )}>
                  {telegramStatus}
                </h3>
              </div>
              <p className="text-[11px] text-muted-foreground font-medium mt-1">
                {telegramStatus === "connected" 
                  ? "Bot connected and listening to channel events." 
                  : telegramStatus === "reconnecting" 
                    ? "Connection interrupted. Re-establishing connection..."
                    : "Message routing is suspended. Service offline."
                }
              </p>
            </>
          )}
        </div>
 
        {/* MongoDB Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium relative overflow-hidden flex flex-col justify-between min-h-[130px] hover:border-muted/80 transition-all duration-200">
          {isCacheLoading ? (
            <div className="flex flex-col gap-3.5 w-full animate-pulse">
              <div className="h-3 bg-muted rounded w-1/3"></div>
              <div className="h-6 bg-muted rounded w-2/3"></div>
              <div className="h-3 bg-muted rounded w-1/2"></div>
            </div>
          ) : isCacheError ? (
            <div className="flex flex-col justify-between h-full w-full">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span className="text-xs font-bold">Database Error</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
                Could not fetch MongoDB status.
              </p>
              <button 
                onClick={() => refetchCache()}
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline cursor-pointer select-none"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry status check</span>
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Database Link</span>
                <Server className={cn(
                  "w-4 h-4",
                  !isMongoDown ? "text-emerald-500" : "text-red-500"
                )} />
              </div>
              <div className="mt-2.5">
                <h3 className={cn(
                  "text-lg font-bold tracking-tight",
                  !isMongoDown ? "text-foreground" : "text-red-500"
                )}>
                  {!isMongoDown ? "Online" : "Offline"}
                </h3>
              </div>
              <p className="text-[11px] text-muted-foreground font-medium mt-1">
                {!isMongoDown 
                  ? "MongoDB connected. Rule configs loaded." 
                  : "Database service down. Forwarding is halted."
                }
              </p>
            </>
          )}
        </div>
 
        {/* Rule Orchestrator Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium relative overflow-hidden flex flex-col justify-between min-h-[130px] hover:border-muted/80 transition-all duration-200">
          {isRulesLoading || isStatsLoading ? (
            <div className="flex flex-col gap-3.5 w-full animate-pulse">
              <div className="h-3 bg-muted rounded w-1/3"></div>
              <div className="h-6 bg-muted rounded w-2/3"></div>
              <div className="h-3 bg-muted rounded w-1/2"></div>
            </div>
          ) : isRulesError || isStatsError ? (
            <div className="flex flex-col justify-between h-full w-full">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span className="text-xs font-bold">Rules Query Error</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
                Could not fetch forwarding rules summary.
              </p>
              <button 
                onClick={() => { refetchRules(); refetchStats(); }}
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline cursor-pointer select-none"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry rules check</span>
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Forwarding Engine</span>
                <Sliders className="w-4 h-4 text-primary" />
              </div>
              <div className="mt-2.5">
                <h3 className="text-lg font-bold text-foreground tracking-tight">
                  {statsData?.active_rules ?? 0} <span className="text-xs font-medium text-muted-foreground">Active</span>
                </h3>
              </div>
              <p className="text-[11px] text-muted-foreground font-medium mt-1">
                Configured: <span className="font-semibold text-foreground">{rulesData?.total ?? 0}</span> total rules.
              </p>
            </>
          )}
        </div>
      </div>
 
      {/* Stats Summary Panel */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
        <div className="flex flex-col gap-0.5 mb-4">
          <h2 className="text-sm font-semibold text-foreground">Delivery Performance</h2>
          <p className="text-[11px] text-muted-foreground font-medium">
            Aggregated traffic statistics processed by the bot engine over the last 24 hours.
          </p>
        </div>
 
        {isStatsLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-muted/40 border border-border/40 rounded-lg p-4 flex flex-col gap-2">
                <div className="h-3 bg-muted rounded w-1/3"></div>
                <div className="h-6 bg-muted rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : isStatsError ? (
          <div className="border border-error-border bg-error-bg text-error p-4 rounded-lg flex flex-col items-center justify-center gap-2">
            <span className="text-xs font-semibold">Failed to load statistics</span>
            <button 
              onClick={() => refetchStats()}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-750 text-white rounded-lg text-xs font-semibold active:scale-[0.98] transition-all cursor-pointer shadow-3xs"
            >
              Retry Load
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Forwarded Stats */}
            <div className="bg-muted/40 border border-border/50 rounded-lg p-4 flex flex-col justify-between hover:border-muted/80 transition-all duration-200">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Send className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-[9px] font-bold uppercase tracking-wider">Forwarded (24h)</span>
              </div>
              <span className="text-xl font-bold text-foreground tracking-tight mt-2.5">
                {statsData?.forwarded_24h ?? 0}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground mt-1">
                Successfully delivered messages.
              </span>
            </div>
 
            {/* Failed Stats */}
            <div className="bg-muted/40 border border-border/50 rounded-lg p-4 flex flex-col justify-between hover:border-muted/80 transition-all duration-200">
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertOctagon className="w-3.5 h-3.5 text-red-500" />
                <span className="text-[9px] font-bold uppercase tracking-wider">Failed (24h)</span>
              </div>
              <span className={cn(
                "text-xl font-bold tracking-tight mt-2.5",
                (statsData?.failed_24h ?? 0) > 0 ? "text-red-500" : "text-foreground"
              )}>
                {statsData?.failed_24h ?? 0}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground mt-1">
                {(statsData?.failed_24h ?? 0) > 0 
                  ? "Requires operation intervention." 
                  : "Zero transmission errors."
                }
              </span>
            </div>
 
            {/* Blocked Stats */}
            <div className="bg-muted/40 border border-border/50 rounded-lg p-4 flex flex-col justify-between hover:border-muted/80 transition-all duration-200">
              <div className="flex items-center gap-2 text-muted-foreground">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-[9px] font-bold uppercase tracking-wider">Blocked (24h)</span>
              </div>
              <span className="text-xl font-bold text-foreground tracking-tight mt-2.5">
                {statsData?.blocked_24h ?? 0}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground mt-1">
                Filtered out by keywords or media rules.
              </span>
            </div>
          </div>
        )}
      </div>
 
      {/* Recent Activity Panel */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex flex-col gap-0.5">
            <h2 className="text-sm font-semibold text-foreground">Recent Activity</h2>
            <p className="text-[11px] text-muted-foreground font-medium">
              Real-time audit trailing of events, filter blockings, and forward successes.
            </p>
          </div>
          <Link 
            to="/logs"
            className="inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline cursor-pointer select-none"
          >
            <span>View all logs</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
 
        {isLogsLoading ? (
          <div className="flex flex-col gap-2.5 animate-pulse">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="h-11 bg-muted rounded-lg w-full border border-border/40"></div>
            ))}
          </div>
        ) : isLogsError ? (
          <div className="border border-error-border bg-error-bg text-error p-6 rounded-lg flex flex-col items-center justify-center gap-2">
            <span className="text-xs font-semibold">Failed to load recent activity logs</span>
            <button 
              onClick={() => refetchLogs()}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold active:scale-[0.98] transition-all cursor-pointer shadow-3xs"
            >
              Retry Logs Fetch
            </button>
          </div>
        ) : !logsData?.items || logsData.items.length === 0 ? (
          <div className="border border-dashed border-border py-10 px-4 text-center rounded-xl">
            <p className="text-xs text-muted-foreground font-semibold">No recent activity found.</p>
            <p className="text-[10px] text-muted-foreground mt-1 opacity-75">
              Activities will appear here once routing rules match message events.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {logsData.items.map((item, index) => (
              <LogRow key={item.timestamp + index} entry={item} />
            ))}
          </div>
        )}
      </div>
 
      <FirstRunWizard open={wizardOpen} onDismiss={handleDismissWizard} />
    </div>
  );
}

import { useLocation, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { healthApi } from "@/api/health";
import { adminApi } from "@/api/admin";
import { queryKeys } from "@/lib/queryKeys";
import { parseApiError } from "@/lib/utils";
import { toast } from "sonner";
import { ChevronRight, AlertTriangle, Menu, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

interface TopBarProps {
  onMenuToggle: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const location = useLocation();
  const queryClient = useQueryClient();
  const [timeAgo, setTimeAgo] = useState<string>("");

  // Refresh Cache mutation
  const refreshCacheMutation = useMutation({
    mutationFn: adminApi.refreshCache,
    onSuccess: (data) => {
      const version = data.cache?.version ?? data.version ?? 0;
      const ruleCount = data.cache?.rule_count ?? data.rule_count ?? 0;
      const sourceCount = data.cache?.source_count ?? data.source_count ?? 0;
      const refreshedAt = data.cache?.refreshed_at ?? data.refreshed_at ?? new Date().toISOString();
      const timeStr = new Date(refreshedAt).toLocaleTimeString();
      toast.success(`Cache rebuilt (v${version}) — ${ruleCount} rules, ${sourceCount} sources at ${timeStr}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.health.cache() });
    },
    onError: (err) => {
      toast.error(parseApiError(err));
    },
  });

  // Telegram connection check (refetch every 10s)
  const { data: telegramData } = useQuery({
    queryKey: queryKeys.health.telegram(),
    queryFn: healthApi.fetchTelegramStatus,
    refetchInterval: 10000,
    staleTime: 0,
  });

  // Ready check for cache health (refetch every 10s)
  const { data: cacheData } = useQuery({
    queryKey: queryKeys.health.cache(),
    queryFn: healthApi.fetchCacheStatus,
    refetchInterval: 10000,
    staleTime: 0,
  });

  const telegramStatus = telegramData?.telegram || "disconnected";
  const cacheRefreshedAt = cacheData?.cache?.refreshed_at;

  const isCacheStale = (() => {
    if (!cacheRefreshedAt) return false;
    const diff = (Date.now() - new Date(cacheRefreshedAt).getTime()) / 1000;
    return diff > 60; // Stale if last refresh is older than 60s
  })();

  useEffect(() => {
    if (!cacheRefreshedAt) return;
    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - new Date(cacheRefreshedAt).getTime()) / 1000);
      if (seconds < 60) {
        setTimeAgo(`${seconds}s`);
      } else {
        const mins = Math.floor(seconds / 60);
        setTimeAgo(`${mins}m`);
      }
    };
    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 5000);
    return () => clearInterval(interval);
  }, [cacheRefreshedAt]);

  const pathnames = location.pathname.split("/").filter((x) => x);
  const breadcrumbs = [
    { label: "Dashboard", path: "/" },
    ...pathnames.map((value, index) => {
      const to = `/${pathnames.slice(0, index + 1).join("/")}`;
      const label = value.charAt(0).toUpperCase() + value.slice(1);
      return { label, path: to };
    }),
  ];

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/80 backdrop-blur-md px-4 md:px-6 select-none transition-all duration-150">
      {/* Breadcrumbs / Mobile Menu Toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted md:hidden cursor-pointer transition-colors duration-150"
          aria-label="Open navigation"
        >
          <Menu className="w-4 h-4" />
        </button>

        <nav className="hidden sm:flex items-center gap-1 text-xs font-medium tracking-tight">
          {breadcrumbs.map((crumb, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            return (
              <div key={crumb.path} className="flex items-center gap-1">
                {idx > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/40" />}
                {isLast ? (
                  <span className="text-foreground font-semibold px-1 py-0.5">{crumb.label}</span>
                ) : (
                  <Link to={crumb.path} className="text-muted-foreground hover:text-foreground hover:bg-muted/55 rounded px-1.5 py-0.5 transition-all">
                    {crumb.label}
                  </Link>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Health Status Dots & Warning Banners */}
      <div className="flex items-center gap-3">
        {/* Rules Cache Stale Warning */}
        {isCacheStale && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-warning-bg border border-warning-border text-warning-foreground shadow-sm">
            <AlertTriangle className="w-3 h-3 animate-bounce" />
            <span>Rules cache stale (last refresh {timeAgo} ago)</span>
          </div>
        )}

        {/* Refresh Cache Button */}
        <button
          onClick={() => refreshCacheMutation.mutate()}
          disabled={refreshCacheMutation.isPending}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border bg-card hover:bg-muted text-[11px] font-semibold text-foreground cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Refresh Cache"
          title="Refresh Rule Cache"
        >
          <RefreshCw className={cn("w-3.5 h-3.5 text-muted-foreground", refreshCacheMutation.isPending && "animate-spin")} />
          <span className="hidden sm:inline">Refresh Cache</span>
        </button>

        {/* Telegram status dot */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg border border-border bg-muted-bg/50">
          <div className="relative flex h-1.5 w-1.5">
            {telegramStatus === "connected" && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75 animate-ping"></span>
            )}
            {telegramStatus === "reconnecting" && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75"></span>
            )}
            {telegramStatus === "disconnected" && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
            )}
            <span
              className={cn(
                "relative inline-flex rounded-full h-1.5 w-1.5",
                telegramStatus === "connected" && "bg-emerald-500",
                telegramStatus === "reconnecting" && "bg-amber-500",
                telegramStatus === "disconnected" && "bg-red-500"
              )}
            />
          </div>
          <span className="text-[10px] font-semibold tracking-wide uppercase text-muted-foreground">
            Telegram: <span className={cn(
              telegramStatus === "connected" && "text-emerald-600 dark:text-emerald-400 font-bold",
              telegramStatus === "reconnecting" && "text-amber-600 dark:text-amber-400 font-bold",
              telegramStatus === "disconnected" && "text-red-600 dark:text-red-400 font-bold",
            )}>{telegramStatus}</span>
          </span>
        </div>
      </div>
    </header>
  );
}

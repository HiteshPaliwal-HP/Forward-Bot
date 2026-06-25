import { useLocation, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { healthApi } from "@/api/health";
import { queryKeys } from "@/lib/queryKeys";
import { ChevronRight, AlertTriangle, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

interface TopBarProps {
  onMenuToggle: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const location = useLocation();
  const [timeAgo, setTimeAgo] = useState<string>("");

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
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 md:px-6 shadow-xs select-none">
      {/* Breadcrumbs / Mobile Menu Toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted md:hidden cursor-pointer"
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <nav className="hidden sm:flex items-center gap-1.5 text-sm font-medium">
          {breadcrumbs.map((crumb, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            return (
              <div key={crumb.path} className="flex items-center gap-1.5">
                {idx > 0 && <ChevronRight className="w-4 h-4 text-muted-foreground/60" />}
                {isLast ? (
                  <span className="text-foreground font-semibold">{crumb.label}</span>
                ) : (
                  <Link to={crumb.path} className="text-muted-foreground hover:text-foreground transition-colors">
                    {crumb.label}
                  </Link>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Health Status Dots & Warning Banners */}
      <div className="flex items-center gap-4">
        {/* Rules Cache Stale Warning */}
        {isCacheStale && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-warning-bg border border-warning-border text-warning-foreground animate-pulse shadow-2xs">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Rules cache stale (last refresh {timeAgo} ago)</span>
          </div>
        )}

        {/* Telegram status dot */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-muted/40">
          <div className="relative flex h-2 w-2">
            {telegramStatus === "connected" && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
            )}
            {telegramStatus === "reconnecting" && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75"></span>
            )}
            {telegramStatus === "disconnected" && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
            )}
            <span
              className={cn(
                "relative inline-flex rounded-full h-2 w-2",
                telegramStatus === "connected" && "bg-emerald-500",
                telegramStatus === "reconnecting" && "bg-amber-500",
                telegramStatus === "disconnected" && "bg-red-500"
              )}
            />
          </div>
          <span className="text-xs font-semibold capitalize text-muted-foreground">
            Telegram: <span className={cn(
              telegramStatus === "connected" && "text-emerald-600 dark:text-emerald-400",
              telegramStatus === "reconnecting" && "text-amber-600 dark:text-amber-400",
              telegramStatus === "disconnected" && "text-red-600 dark:text-red-400",
            )}>{telegramStatus}</span>
          </span>
        </div>
      </div>
    </header>
  );
}

import { useTheme } from "@/contexts/ThemeContext";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { healthApi } from "@/api/health";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { 
  Monitor, 
  Sun, 
  Moon, 
  Database, 
  Clock, 
  Info, 
  LogOut, 
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [sessionUptime, setSessionUptime] = useState<string>("0h 0m 0s");

  useEffect(() => {
    const startTime = Date.now();
    const timer = setInterval(() => {
      const diff = Math.floor((Date.now() - startTime) / 1000);
      const hours = Math.floor(diff / 3600);
      const minutes = Math.floor((diff % 3600) / 60);
      const seconds = diff % 60;
      setSessionUptime(`${hours}h ${minutes}m ${seconds}s`);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Liveness Check Query
  const { 
    refetch: refetchHealth
  } = useQuery({
    queryKey: queryKeys.health.status(),
    queryFn: healthApi.fetchHealth,
    staleTime: 30_000,
  });

  // Database / Ready Check Query
  const { 
    data: cacheData,
    isLoading: isCacheLoading,
    refetch: refetchCache
  } = useQuery({
    queryKey: queryKeys.health.cache(),
    queryFn: healthApi.fetchCacheStatus,
    staleTime: 30_000,
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      toast.success("Successfully logged out");
      navigate("/login");
    },
    onError: () => {
      toast.error("Logout failed — please try again.");
    },
  });

  // Resolve Version and MongoDB status
  const mongoStatus = cacheData?.mongodb || "down";
  const serviceVersion = cacheData?.cache?.version !== undefined 
    ? `v0.1.${cacheData.cache.version}` 
    : "v0.1.0";

  return (
    <div className="flex flex-col gap-5 max-w-4xl select-none animate-fade-in pb-16">
      {/* Header */}
      <div className="flex flex-col gap-0.5">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-xs text-muted-foreground font-medium">
          Manage system preferences, monitor system services, and control your current session.
        </p>
      </div>

      {/* Main Settings Body */}
      <div className="flex flex-col gap-5">
        
        {/* Theme Settings Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
          <div className="flex flex-col gap-0.5 mb-4">
            <h2 className="text-xs font-bold text-foreground uppercase tracking-wide">Appearance</h2>
            <p className="text-[11px] text-muted-foreground font-medium">
              Choose your preferred interface color theme.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {/* System Option */}
            <button
              onClick={() => setTheme("system")}
              className={cn(
                "flex flex-col items-center justify-center p-3 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 active:scale-[0.98]",
                theme === "system" 
                  ? "bg-muted border-border text-foreground font-bold shadow-2xs" 
                  : "bg-card border-border text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Monitor className="w-4 h-4 text-muted-foreground/80" />
              <span className="text-[11px] font-semibold">System</span>
            </button>

            {/* Light Option */}
            <button
              onClick={() => setTheme("light")}
              className={cn(
                "flex flex-col items-center justify-center p-3 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 active:scale-[0.98]",
                theme === "light" 
                  ? "bg-muted border-border text-foreground font-bold shadow-2xs" 
                  : "bg-card border-border text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Sun className="w-4 h-4 text-muted-foreground/80" />
              <span className="text-[11px] font-semibold">Light</span>
            </button>

            {/* Dark Option */}
            <button
              onClick={() => setTheme("dark")}
              className={cn(
                "flex flex-col items-center justify-center p-3 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 active:scale-[0.98]",
                theme === "dark" 
                  ? "bg-muted border-border text-foreground font-bold shadow-2xs" 
                  : "bg-card border-border text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Moon className="w-4 h-4 text-muted-foreground/80" />
              <span className="text-[11px] font-semibold">Dark</span>
            </button>
          </div>
        </div>

        {/* System Information Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex flex-col gap-0.5">
              <h2 className="text-xs font-bold text-foreground uppercase tracking-wide">System Information</h2>
              <p className="text-[11px] text-muted-foreground font-medium">
                Live environment information for debugging and health auditing.
              </p>
            </div>
            <button 
              onClick={() => { refetchHealth(); refetchCache(); }}
              className="inline-flex items-center gap-1.5 text-xs text-primary font-bold hover:underline cursor-pointer select-none"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Refresh Status</span>
            </button>
          </div>

          <div className="divide-y divide-border">
            {/* Version Row */}
            <div className="py-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <Info className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Service Version</span>
                  <span className="text-[10px] text-muted-foreground">Currently deployed backend version</span>
                </div>
              </div>
              <span className="text-xs font-mono font-bold bg-muted px-2 py-0.5 rounded-lg text-foreground border border-border">
                {isCacheLoading ? "Loading..." : serviceVersion}
              </span>
            </div>

            {/* MongoDB Connection Row */}
            <div className="py-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Database Connectivity</span>
                  <span className="text-[10px] text-muted-foreground">MongoDB replica set status</span>
                </div>
              </div>
              <div>
                {isCacheLoading ? (
                  <span className="text-xs text-muted-foreground font-semibold">Checking...</span>
                ) : mongoStatus === "up" ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-success-bg border border-success-border text-success-foreground">
                    <CheckCircle2 className="w-3 h-3 stroke-[2.5px]" />
                    <span>Connected</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-error-bg border border-error-border text-error">
                    <AlertCircle className="w-3 h-3 stroke-[2.5px]" />
                    <span>Disconnected</span>
                  </span>
                )}
              </div>
            </div>

            {/* Session TTL Row */}
            <div className="py-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Session Lifetime</span>
                  <span className="text-[10px] text-muted-foreground">Security cookie expiration threshold</span>
                </div>
              </div>
              <span className="text-xs font-semibold text-foreground">24 Hours (HttpOnly)</span>
            </div>

            {/* Session Uptime Row */}
            <div className="py-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Active Session Duration</span>
                  <span className="text-[10px] text-muted-foreground">Time elapsed since application load</span>
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-foreground tabular-nums bg-muted px-2 py-0.5 rounded-lg border border-border">
                {sessionUptime}
              </span>
            </div>
          </div>
        </div>

        {/* Danger Zone / Session Management */}
        <div className="bg-card border border-red-500/20 rounded-xl p-5 shadow-premium">
          <div className="flex flex-col gap-0.5 mb-4">
            <h2 className="text-xs font-bold text-red-500 uppercase tracking-wide">Session Management</h2>
            <p className="text-[11px] text-muted-foreground font-medium">
              Terminate your active operator credentials session.
            </p>
          </div>

          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-bold text-foreground">Sign Out</span>
              <span className="text-[10px] text-muted-foreground">Clear HttpOnly browser credentials.</span>
            </div>
            <button
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-750 text-white rounded-lg text-xs font-semibold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>{logoutMutation.isPending ? "Logging out..." : "Log Out"}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

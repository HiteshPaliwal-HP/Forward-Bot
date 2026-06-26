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
    <div className="flex flex-col gap-6 max-w-4xl select-none">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground font-medium">
          Manage system preferences, monitor system services, and control your current session.
        </p>
      </div>

      {/* Main Settings Body */}
      <div className="flex flex-col gap-6">
        
        {/* Theme Settings Card */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-2xs">
          <div className="flex flex-col gap-1 mb-5">
            <h2 className="text-lg font-bold text-foreground">Appearance</h2>
            <p className="text-xs text-muted-foreground font-medium">
              Choose your preferred interface color theme.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {/* System Option */}
            <button
              onClick={() => setTheme("system")}
              className={cn(
                "flex flex-col items-center justify-center p-4 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                theme === "system" 
                  ? "bg-primary-foreground border-primary text-foreground font-bold shadow-3xs" 
                  : "bg-muted-bg border-border text-muted-foreground hover:bg-muted/10 hover:text-foreground"
              )}
            >
              <Monitor className="w-5 h-5" />
              <span className="text-xs">System</span>
            </button>

            {/* Light Option */}
            <button
              onClick={() => setTheme("light")}
              className={cn(
                "flex flex-col items-center justify-center p-4 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                theme === "light" 
                  ? "bg-primary-foreground border-primary text-foreground font-bold shadow-3xs" 
                  : "bg-muted-bg border-border text-muted-foreground hover:bg-muted/10 hover:text-foreground"
              )}
            >
              <Sun className="w-5 h-5" />
              <span className="text-xs">Light</span>
            </button>

            {/* Dark Option */}
            <button
              onClick={() => setTheme("dark")}
              className={cn(
                "flex flex-col items-center justify-center p-4 rounded-lg border text-center cursor-pointer transition-all duration-200 gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                theme === "dark" 
                  ? "bg-primary-foreground border-primary text-foreground font-bold shadow-3xs" 
                  : "bg-muted-bg border-border text-muted-foreground hover:bg-muted/10 hover:text-foreground"
              )}
            >
              <Moon className="w-5 h-5" />
              <span className="text-xs">Dark</span>
            </button>
          </div>
        </div>

        {/* System Information Card */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-2xs">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <div className="flex flex-col gap-1">
              <h2 className="text-lg font-bold text-foreground">System Information</h2>
              <p className="text-xs text-muted-foreground font-medium">
                Live environment information for debugging and health auditing.
              </p>
            </div>
            <button 
              onClick={() => { refetchHealth(); refetchCache(); }}
              className="inline-flex items-center gap-1.5 text-xs text-primary font-bold hover:underline cursor-pointer select-none"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Status</span>
            </button>
          </div>

          <div className="divide-y divide-border">
            {/* Version Row */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Info className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground">Service Version</span>
                  <span className="text-xs text-muted-foreground">Currently deployed backend version</span>
                </div>
              </div>
              <span className="text-sm font-mono font-bold bg-muted px-2.5 py-1 rounded text-foreground">
                {isCacheLoading ? "Loading..." : serviceVersion}
              </span>
            </div>

            {/* MongoDB Connection Row */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground">Database Connectivity</span>
                  <span className="text-xs text-muted-foreground">MongoDB replica set status</span>
                </div>
              </div>
              <div>
                {isCacheLoading ? (
                  <span className="text-sm text-muted-foreground font-semibold">Checking...</span>
                ) : mongoStatus === "up" ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-success-bg border border-success-border text-success-foreground">
                    <CheckCircle2 className="w-3 h-3 stroke-[2.5px]" />
                    <span>Connected</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-error-bg border border-error-border text-error">
                    <AlertCircle className="w-3 h-3 stroke-[2.5px]" />
                    <span>Disconnected</span>
                  </span>
                )}
              </div>
            </div>

            {/* Session TTL Row */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground">Session Lifetime</span>
                  <span className="text-xs text-muted-foreground">Security cookie expiration threshold</span>
                </div>
              </div>
              <span className="text-sm font-semibold text-foreground">24 Hours (HttpOnly)</span>
            </div>

            {/* Session Uptime Row */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground">Active Session Duration</span>
                  <span className="text-xs text-muted-foreground">Time elapsed since application load</span>
                </div>
              </div>
              <span className="text-sm font-mono font-bold text-foreground tabular-nums">
                {sessionUptime}
              </span>
            </div>
          </div>
        </div>

        {/* Danger Zone / Session Management */}
        <div className="bg-card border border-error-border/40 rounded-xl p-6 shadow-2xs">
          <div className="flex flex-col gap-1 mb-5">
            <h2 className="text-lg font-bold text-error">Session Management</h2>
            <p className="text-xs text-muted-foreground font-medium">
              Terminate your active operator credentials session.
            </p>
          </div>

          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-bold text-foreground">Sign Out</span>
              <span className="text-xs text-muted-foreground">Clear HttpOnly browser credentials.</span>
            </div>
            <button
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-error text-white rounded-md text-xs font-bold hover:bg-red-700 active:scale-[0.98] transition-all cursor-pointer shadow-3xs disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              <LogOut className="w-4 h-4" />
              <span>{logoutMutation.isPending ? "Logging out..." : "Log Out"}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { healthApi } from "@/api/health";
import { queryKeys } from "@/lib/queryKeys";
import { apiClient } from "@/api/client";
import { AlertCircle, RefreshCw, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export function DegradedBanner() {
  const navigate = useNavigate();
  const [reconnectState, setReconnectState] = useState<"idle" | "loading" | "success" | "failure">("idle");
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Query health status (polls every 10s)
  const { data: telegramData, refetch: refetchTelegram } = useQuery({
    queryKey: queryKeys.health.telegram(),
    queryFn: healthApi.fetchTelegramStatus,
    refetchInterval: 10000,
    staleTime: 0,
  });

  const { data: cacheData, refetch: refetchCache } = useQuery({
    queryKey: queryKeys.health.cache(),
    queryFn: healthApi.fetchCacheStatus,
    refetchInterval: 10000,
    staleTime: 0,
  });

  const telegramStatus = telegramData?.telegram || "disconnected";
  const isMongoDown = cacheData?.mongodb !== "up";

  const isDegraded = telegramStatus === "disconnected" || telegramStatus === "reconnecting" || isMongoDown;

  const reconnectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/admin/reconnect");
    },
    onSuccess: () => {
      setReconnectState("loading");
      
      // Poll Telegram status to check when it transitions to connected
      let attempts = 0;
      intervalRef.current = window.setInterval(async () => {
        attempts++;
        const { data: tgStatus } = await refetchTelegram();
        const { data: cStatus } = await refetchCache();
        
        if (tgStatus?.telegram === "connected" && cStatus?.mongodb === "up") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setReconnectState("success");
          setTimeout(() => setReconnectState("idle"), 2000);
        } else if (attempts >= 15) {
          // 30 seconds timeout
          if (intervalRef.current) clearInterval(intervalRef.current);
          setReconnectState("failure");
          toast.error("Reconnect failed — see logs.", {
            action: {
              label: "Open Logs",
              onClick: () => navigate("/logs"),
            },
          });
          setTimeout(() => setReconnectState("idle"), 3000);
        }
      }, 2000);
    },
    onError: () => {
      setReconnectState("failure");
      toast.error("Reconnect trigger failed — see logs.");
      setTimeout(() => setReconnectState("idle"), 3000);
    }
  });

  if (!isDegraded) return null;

  const bannerText = isMongoDown
    ? "Database service is unreachable. Message forwarding is offline."
    : `Telegram service connection is ${telegramStatus}. Message forwarding is offline or degraded.`;

  return (
    <div 
      role="alert" 
      aria-live="assertive" 
      className="w-full bg-degraded-bg border-b border-degraded-border text-degraded-foreground py-3 px-4 flex flex-col sm:flex-row items-center justify-between gap-3 select-none"
    >
      <div className="flex items-center gap-2">
        <AlertCircle className="w-5 h-5 flex-shrink-0 text-error animate-pulse" />
        <span className="text-sm font-semibold tracking-tight leading-normal">{bannerText}</span>
      </div>

      <button
        disabled={reconnectState === "loading" || reconnectState === "success"}
        onClick={() => reconnectMutation.mutate()}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold border cursor-pointer select-none transition-all duration-300",
          reconnectState === "idle" && "bg-error text-white border-transparent hover:bg-red-700 active:scale-[0.97]",
          reconnectState === "loading" && "bg-muted text-muted-foreground border-border cursor-wait opacity-75",
          reconnectState === "success" && "bg-success text-white border-transparent",
          reconnectState === "failure" && "bg-error text-white border-transparent animate-shake"
        )}
      >
        {reconnectState === "idle" && (
          <>
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reconnect</span>
          </>
        )}
        {reconnectState === "loading" && (
          <>
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Reconnecting...</span>
          </>
        )}
        {reconnectState === "success" && (
          <>
            <Check className="w-3.5 h-3.5 stroke-[3px]" />
            <span>Connected</span>
          </>
        )}
        {reconnectState === "failure" && (
          <>
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Retry Failed</span>
          </>
        )}
      </button>
    </div>
  );
}

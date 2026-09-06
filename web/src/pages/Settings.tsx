import { useTheme } from "@/contexts/ThemeContext";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { healthApi } from "@/api/health";
import { telegramAuthApi } from "@/api/telegramAuth";
import { adminApi } from "@/api/admin";
import { queryKeys } from "@/lib/queryKeys";
import { parseApiError } from "@/lib/utils";
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
  AlertCircle,
  Radio,
  ShieldAlert,
  Send,
  KeyRound,
  Trash2
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [sessionUptime, setSessionUptime] = useState<string>("0h 0m 0s");

  // Telegram Session Auth Form State
  const [phoneInput, setPhoneInput] = useState<string>("");
  const [otpInput, setOtpInput] = useState<string>("");
  const [passwordInput, setPasswordInput] = useState<string>("");
  const [authStep, setAuthStep] = useState<"idle" | "otp" | "2fa">("idle");
  const [otpCountdown, setOtpCountdown] = useState<number>(0);
  const [authError, setAuthError] = useState<string | null>(null);

  // Terminate Modal State
  const [isTerminateModalOpen, setIsTerminateModalOpen] = useState<boolean>(false);
  const [terminateConfirmInput, setTerminateConfirmInput] = useState<string>("");

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

  // OTP Throttle Countdown Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (otpCountdown > 0) {
      interval = setInterval(() => {
        setOtpCountdown((prev) => prev - 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [otpCountdown > 0]);

  // Liveness Check Query
  const { refetch: refetchHealth } = useQuery({
    queryKey: queryKeys.health.status(),
    queryFn: healthApi.fetchHealth,
    staleTime: 30_000,
  });

  // Database / Cache Health Query
  const { 
    data: cacheData,
    isLoading: isCacheLoading,
    refetch: refetchCache
  } = useQuery({
    queryKey: queryKeys.health.cache(),
    queryFn: healthApi.fetchCacheStatus,
    staleTime: 30_000,
  });

  // Telegram Auth Status Query
  const { 
    data: telegramAuthStatus,
    isLoading: isTelegramAuthLoading,
    refetch: refetchTelegramAuth
  } = useQuery({
    queryKey: queryKeys.telegramAuth.status(),
    queryFn: telegramAuthApi.getStatus,
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  // Refresh Cache Mutation
  const refreshCacheMutation = useMutation({
    mutationFn: adminApi.refreshCache,
    onSuccess: (data) => {
      const version = data.cache?.version ?? data.version ?? 0;
      const ruleCount = data.cache?.rule_count ?? data.rule_count ?? 0;
      const sourceCount = data.cache?.source_count ?? data.source_count ?? 0;
      toast.success(`Cache rebuilt (v${version}) — ${ruleCount} rules, ${sourceCount} sources`);
      queryClient.invalidateQueries({ queryKey: queryKeys.health.cache() });
    },
    onError: (err) => {
      toast.error(parseApiError(err));
    },
  });

  // Start Auth (Send OTP) Mutation
  const startAuthMutation = useMutation({
    mutationFn: (phone?: string) => telegramAuthApi.startAuth(phone),
    onSuccess: () => {
      setAuthStep("otp");
      setOtpCountdown(60);
      setAuthError(null);
      toast.success("OTP code sent to your Telegram account");
    },
    onError: (err) => {
      const errMsg = parseApiError(err);
      setAuthError(errMsg);
      toast.error(errMsg);
    },
  });

  // Verify Auth (OTP / 2FA) Mutation
  const verifyAuthMutation = useMutation({
    mutationFn: (payload: { otp: string; password?: string; phone?: string }) => 
      telegramAuthApi.verifyAuth(payload),
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setAuthStep("2fa");
        setAuthError(null);
        toast.info("Two-factor authentication (2FA) required. Please enter your 2FA password.");
      } else {
        toast.success("Telegram session connected successfully!");
        setAuthStep("idle");
        setOtpInput("");
        setPasswordInput("");
        setAuthError(null);
        queryClient.invalidateQueries({ queryKey: queryKeys.telegramAuth.all });
        queryClient.invalidateQueries({ queryKey: queryKeys.health.all });
      }
    },
    onError: (err) => {
      const errMsg = parseApiError(err);
      setAuthError(errMsg);
      toast.error(errMsg);
    },
  });

  // Terminate Session Mutation
  const terminateSessionMutation = useMutation({
    mutationFn: telegramAuthApi.terminateSession,
    onSuccess: () => {
      toast.success("Telegram session terminated");
      setIsTerminateModalOpen(false);
      setTerminateConfirmInput("");
      queryClient.invalidateQueries({ queryKey: queryKeys.telegramAuth.status() });
      queryClient.invalidateQueries({ queryKey: queryKeys.health.telegram() });
      queryClient.invalidateQueries({ queryKey: queryKeys.health.all });
    },
    onError: (err) => {
      toast.error(parseApiError(err));
    },
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

  const isConnected = telegramAuthStatus?.connected ?? false;
  const isPhoneRequired = telegramAuthStatus?.phone_required ?? true;
  const displayPhone = telegramAuthStatus?.phone ?? null;
  const sessionPath = telegramAuthStatus?.session_path ?? "";

  const handleSendOtp = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isPhoneRequired && !phoneInput.trim()) {
      setAuthError("Phone number is required");
      return;
    }
    startAuthMutation.mutate(phoneInput.trim() || undefined);
  };

  const handleVerifyOtp = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!otpInput.trim()) {
      setAuthError("OTP code is required");
      return;
    }
    verifyAuthMutation.mutate({
      otp: otpInput.trim(),
      password: passwordInput.trim() || undefined,
      phone: phoneInput.trim() || undefined,
    });
  };

  const isTerminateConfirmValid = terminateConfirmInput.trim().toLowerCase() === "terminate";

  return (
    <div className="flex flex-col gap-5 max-w-4xl select-none animate-fade-in pb-16">
      {/* Header */}
      <div className="flex flex-col gap-0.5">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-xs text-muted-foreground font-medium">
          Manage system preferences, control your Telegram session, and monitor system services.
        </p>
      </div>

      {/* Main Settings Body */}
      <div className="flex flex-col gap-5">
        
        {/* Telegram Session Control Card (UX-DR26, UX-DR27, UX-DR28, FR-46..FR-50) */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-primary" />
                <h2 className="text-xs font-bold text-foreground uppercase tracking-wide">Telegram Session Control</h2>
              </div>
              <p className="text-[11px] text-muted-foreground font-medium">
                Manage the active Telegram userbot session used for message ingestion and forwarding.
              </p>
            </div>

            {/* Status Pill */}
            {isTelegramAuthLoading ? (
              <span className="text-xs text-muted-foreground font-semibold">Loading status...</span>
            ) : isConnected ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse inline-block mr-1.5" />
                CONNECTED
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block mr-1.5" />
                DISCONNECTED
              </span>
            )}
          </div>

          {/* Session Content logic */}
          {isConnected ? (
            /* CONNECTED STATE */
            <div className="flex flex-col gap-4 pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-muted/40 p-3.5 rounded-lg border border-border">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Connected Account</span>
                  <span className="text-xs font-bold font-mono text-foreground">
                    {displayPhone || "Authenticated Telegram Session"}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Session Storage Path</span>
                  <span className="text-xs font-mono font-medium text-foreground truncate" title={sessionPath}>
                    {sessionPath || "Default runtime directory"}
                  </span>
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  onClick={() => {
                    setTerminateConfirmInput("");
                    setIsTerminateModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/30 text-red-500 hover:bg-red-500/10 hover:text-red-600 text-xs font-semibold cursor-pointer transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Terminate Session</span>
                </button>
              </div>
            </div>
          ) : (
            /* DISCONNECTED STATE */
            <div className="flex flex-col gap-4 pt-2">
              {/* Inline Error Alert */}
              {authError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium">
                  <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <form onSubmit={authStep === "idle" ? handleSendOtp : handleVerifyOtp} className="flex flex-col gap-3">
                {/* Step 1: Phone Input */}
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="telegram-phone-input" className="text-xs font-semibold text-foreground">
                    Telegram Phone Number (E.164 format)
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="telegram-phone-input"
                      type="tel"
                      placeholder="+1234567890"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      disabled={startAuthMutation.isPending || verifyAuthMutation.isPending}
                      className="flex-1 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={
                        startAuthMutation.isPending ||
                        otpCountdown > 0 ||
                        (isPhoneRequired && !phoneInput.trim())
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground hover:opacity-90 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer whitespace-nowrap"
                    >
                      <Send className="w-3 h-3" />
                      <span>
                        {startAuthMutation.isPending
                          ? "Sending..."
                          : otpCountdown > 0
                          ? `Resend in ${otpCountdown}s`
                          : "Send OTP"}
                      </span>
                    </button>
                  </div>
                  <span className="text-[10px] text-muted-foreground">
                    Format: +&lt;country_code&gt;&lt;number&gt; (e.g. +14155552671)
                  </span>
                </div>

                {/* Step 2: OTP Input (rendered after /start success) */}
                {(authStep === "otp" || authStep === "2fa") && (
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-border">
                    <label htmlFor="telegram-otp-input" className="text-xs font-semibold text-foreground">
                      6-Digit OTP Code
                    </label>
                    <input
                      id="telegram-otp-input"
                      type="text"
                      maxLength={6}
                      placeholder="123456"
                      value={otpInput}
                      onChange={(e) => setOtpInput(e.target.value)}
                      disabled={verifyAuthMutation.isPending}
                      className="w-full px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground disabled:opacity-50"
                    />
                  </div>
                )}

                {/* Step 3: 2FA Password Input (rendered if 202 requires_2fa) */}
                {authStep === "2fa" && (
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-border">
                    <label htmlFor="telegram-2fa-input" className="text-xs font-semibold text-foreground">
                      Two-Factor Authentication (2FA) Password
                    </label>
                    <div className="relative">
                      <input
                        id="telegram-2fa-input"
                        type="password"
                        placeholder="Enter 2FA password"
                        value={passwordInput}
                        onChange={(e) => setPasswordInput(e.target.value)}
                        disabled={verifyAuthMutation.isPending}
                        className="w-full px-3 py-1.5 bg-card border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground disabled:opacity-50"
                      />
                    </div>
                  </div>
                )}

                {/* Submit Verification Button */}
                {(authStep === "otp" || authStep === "2fa") && (
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="submit"
                      disabled={verifyAuthMutation.isPending || !otpInput.trim()}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-sm"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>
                        {verifyAuthMutation.isPending
                          ? "Connecting..."
                          : authStep === "2fa"
                          ? "Submit 2FA Password"
                          : "Connect Telegram"}
                      </span>
                    </button>
                  </div>
                )}
              </form>
            </div>
          )}
        </div>

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

        {/* System Information & Cache Control Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-premium">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex flex-col gap-0.5">
              <h2 className="text-xs font-bold text-foreground uppercase tracking-wide">System Information & Cache</h2>
              <p className="text-[11px] text-muted-foreground font-medium">
                Live environment information and RuleCache controls.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => refreshCacheMutation.mutate()}
                disabled={refreshCacheMutation.isPending}
                className="inline-flex items-center gap-1.5 text-xs text-primary font-bold hover:underline cursor-pointer select-none disabled:opacity-50"
              >
                <RefreshCw className={cn("w-3 h-3", refreshCacheMutation.isPending && "animate-spin")} />
                <span>Refresh Cache</span>
              </button>
              <span className="text-muted-foreground/40">•</span>
              <button 
                onClick={() => { refetchHealth(); refetchCache(); refetchTelegramAuth(); }}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground font-semibold hover:text-foreground cursor-pointer select-none"
              >
                <span>Check Status</span>
              </button>
            </div>
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
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-3 h-3 stroke-[2.5px]" />
                    <span>Connected</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>{logoutMutation.isPending ? "Logging out..." : "Log Out"}</span>
            </button>
          </div>
        </div>

      </div>

      {/* Terminate Telegram Session Confirmation Modal (AC: #6, UX-DR28) */}
      <AlertDialog open={isTerminateModalOpen} onOpenChange={setIsTerminateModalOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Terminate Telegram Session?</AlertDialogTitle>
            <AlertDialogDescription className="text-xs text-muted-foreground">
              Terminating the Telegram session will disconnect the forwarding worker. Incoming messages will be dropped.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex flex-col gap-2 py-2">
            <label htmlFor="terminate-confirm-input" className="text-xs font-semibold text-foreground">
              Type <code className="bg-muted px-1 py-0.5 rounded text-red-500 font-mono">terminate</code> to confirm:
            </label>
            <input
              id="terminate-confirm-input"
              type="text"
              placeholder="terminate"
              value={terminateConfirmInput}
              onChange={(e) => setTerminateConfirmInput(e.target.value)}
              className="w-full px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-red-500/20 text-foreground"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setIsTerminateModalOpen(false);
                setTerminateConfirmInput("");
              }}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={!isTerminateConfirmValid || terminateSessionMutation.isPending}
              onClick={() => terminateSessionMutation.mutate()}
              className="bg-red-600 hover:bg-red-700 text-white border-none"
            >
              {terminateSessionMutation.isPending ? "Terminating..." : "Confirm Terminate"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

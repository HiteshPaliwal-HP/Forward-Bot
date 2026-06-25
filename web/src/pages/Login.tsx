import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, Eye, EyeOff } from "lucide-react";
import { authApi } from "@/api/auth";
import { queryClient } from "@/lib/queryClient";
import { Button } from "@/components/shared/Button";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const returnUrl = searchParams.get("return") || "/";

  // Check on mount if session expired
  useEffect(() => {
    if (searchParams.get("return")) {
      toast.error("Session expired — sign in to continue.", {
        id: "session-expired-toast", // Prevent duplicate toasts
      });
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("API Key is required");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await authApi.login(apiKey);
      
      // Invalidate the auth me query cache
      await queryClient.invalidateQueries();
      
      toast.success("Successfully signed in");
      
      // Redirect back
      navigate(returnUrl);
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError("Invalid API key");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12 select-none">
      <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-lg p-8 flex flex-col gap-6">
        {/* Header Logo */}
        <div className="flex flex-col items-center text-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold text-2xl select-none">
            F
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Forward Bot</h1>
            <p className="text-sm text-muted-foreground mt-1">Sign in to operate your forwarding pipeline</p>
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="api-key-input" className="text-xs font-semibold text-muted-foreground">
              API Key
            </label>
            <div className="relative flex items-center">
              <div className="absolute left-3 text-muted-foreground pointer-events-none">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                id="api-key-input"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your dashboard API Key..."
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  if (error) setError(null);
                }}
                disabled={isLoading}
                className="w-full pl-10 pr-10 py-2.5 bg-muted/30 border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 transition-all"
                aria-invalid={!!error}
                aria-describedby={error ? "api-key-error" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 p-1 rounded-md text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                title={showPassword ? "Hide API key" : "Show API key"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {error && (
              <span id="api-key-error" role="alert" className="text-xs text-error font-medium mt-1">
                {error}
              </span>
            )}
          </div>

          <Button type="submit" disabled={isLoading} className="w-full mt-2">
            {isLoading ? "Signing in..." : "Sign In"}
          </Button>
        </form>
      </div>
    </div>
  );
}

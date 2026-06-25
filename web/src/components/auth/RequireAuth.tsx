import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-muted-foreground animate-pulse">Checking credentials...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    const returnPath = location.pathname + location.search;
    return <Navigate to={`/login?return=${encodeURIComponent(returnPath)}`} replace />;
  }

  return <>{children}</>;
}

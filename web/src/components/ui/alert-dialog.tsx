import React, { useEffect } from "react";
import { Button } from "@/components/shared";
import { cn } from "@/lib/utils";

interface AlertDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

export function AlertDialog({ open, onOpenChange, children }: AlertDialogProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop overlay */}
      <div 
        className="fixed inset-0 bg-black/55 backdrop-blur-xs transition-opacity duration-200" 
        onClick={() => onOpenChange?.(false)} 
      />
      {/* Dialog content wrapper */}
      <div className="relative bg-card border border-border rounded-lg shadow-lg max-w-lg w-full p-6 animate-in fade-in zoom-in-95 duration-200 z-10">
        {children}
      </div>
    </div>
  );
}

export function AlertDialogContent({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("space-y-4", className)}>{children}</div>;
}

export function AlertDialogHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)}>{children}</div>;
}

export function AlertDialogFooter({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 space-y-2 space-y-reverse sm:space-y-0 mt-4", className)}>{children}</div>;
}

export function AlertDialogTitle({ className, children }: { className?: string; children: React.ReactNode }) {
  return <h2 className={cn("text-lg font-semibold text-foreground", className)}>{children}</h2>;
}

export function AlertDialogDescription({ className, children }: { className?: string; children: React.ReactNode }) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}

export function AlertDialogAction({ onClick, disabled, className, children }: { onClick?: () => void; disabled?: boolean; className?: string; children: React.ReactNode }) {
  return (
    <Button variant="default" onClick={onClick} disabled={disabled} className={className}>
      {children}
    </Button>
  );
}

export function AlertDialogCancel({ onClick, disabled, className, children }: { onClick?: () => void; disabled?: boolean; className?: string; children: React.ReactNode }) {
  return (
    <Button variant="outline" onClick={onClick} disabled={disabled} className={className}>
      {children}
    </Button>
  );
}

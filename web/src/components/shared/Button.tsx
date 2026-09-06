import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none border border-transparent active:scale-[0.98]",
          // Variants
          variant === "default" && "bg-primary text-primary-foreground hover:bg-color-active-hover shadow-sm",
          variant === "destructive" && "bg-red-600 text-white hover:bg-red-700 shadow-sm",
          variant === "outline" && "border-border bg-transparent hover:bg-muted-bg hover:text-foreground",
          variant === "secondary" && "bg-muted text-foreground hover:bg-color-border/60",
          variant === "ghost" && "hover:bg-muted hover:text-foreground",
          variant === "link" && "underline-offset-4 hover:underline text-primary p-0 border-0 active:scale-100",
          // Sizes
          size === "default" && "h-9 py-1.5 px-3.5 text-xs",
          size === "sm" && "h-8 px-2.5 rounded-lg text-[11px]",
          size === "lg" && "h-10 px-6 rounded-lg text-xs",
          size === "icon" && "h-9 w-9 p-0",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

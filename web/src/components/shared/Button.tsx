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
          "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none",
          // Variants
          variant === "default" && "bg-primary text-primary-foreground hover:bg-color-active-hover shadow",
          variant === "destructive" && "bg-color-error text-white hover:bg-red-700 shadow",
          variant === "outline" && "border border-border bg-transparent hover:bg-muted hover:text-foreground",
          variant === "secondary" && "bg-muted text-foreground hover:bg-color-border",
          variant === "ghost" && "hover:bg-muted hover:text-foreground",
          variant === "link" && "underline-offset-4 hover:underline text-primary",
          // Sizes
          size === "default" && "h-10 py-2 px-4 text-sm",
          size === "sm" && "h-9 px-3 rounded-md text-xs",
          size === "lg" && "h-11 px-8 rounded-md text-sm",
          size === "icon" && "h-10 w-10",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

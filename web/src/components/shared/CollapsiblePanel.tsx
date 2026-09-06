import React, { useState, useId } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CollapsiblePanelProps {
  title: string;
  summary: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  isOpen?: boolean;
  onToggle?: () => void;
}

export function CollapsiblePanel({
  title,
  summary,
  children,
  defaultOpen = false,
  className,
  isOpen: controlledIsOpen,
  onToggle
}: CollapsiblePanelProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(defaultOpen);
  const panelId = useId();

  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.();
    } else {
      setInternalIsOpen(!isOpen);
    }
  };

  return (
    <div className={cn("border border-border rounded-xl bg-card overflow-hidden transition-all duration-200 shadow-premium", className)}>
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-3.5 hover:bg-muted/40 text-left transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
          <span className="text-xs font-bold tracking-tight text-foreground">{title}</span>
          <span className="text-[10px] text-muted-foreground font-medium">{summary}</span>
        </div>
        <ChevronDown 
          className={cn(
            "w-4 h-4 text-muted-foreground/60 transition-transform duration-300 ease-in-out flex-shrink-0",
            isOpen && "rotate-180"
          )}
        />
      </button>
      <div 
        id={panelId}
        aria-hidden={!isOpen}
        className={cn(
          "grid transition-all duration-300 ease-in-out border-border bg-card",
          isOpen ? "grid-rows-[1fr] opacity-100 border-t" : "grid-rows-[0fr] opacity-0"
        )}
      >
        <div className="overflow-hidden">
          <div className="p-4 select-text bg-muted/10">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

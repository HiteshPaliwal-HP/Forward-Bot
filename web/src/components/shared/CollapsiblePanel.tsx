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
    <div className={cn("border border-border rounded-lg bg-card overflow-hidden transition-all duration-200 shadow-2xs", className)}>
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/30 text-left transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
          <span className="font-semibold text-foreground">{title}</span>
          <span className="text-sm text-secondary font-medium">{summary}</span>
        </div>
        <ChevronDown 
          className={cn(
            "w-5 h-5 text-muted-foreground transition-transform duration-300 ease-in-out flex-shrink-0",
            isOpen && "rotate-180"
          )}
        />
      </button>
      <div 
        id={panelId}
        aria-hidden={!isOpen}
        className={cn(
          "grid transition-all duration-300 ease-in-out border-border bg-muted/5",
          isOpen ? "grid-rows-[1fr] opacity-100 border-t" : "grid-rows-[0fr] opacity-0"
        )}
      >
        <div className="overflow-hidden">
          <div className="p-4 select-text">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

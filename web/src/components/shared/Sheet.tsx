import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Sheet({ isOpen, onClose, children }: SheetProps) {
  // Disable body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop overlay */}
      <div 
        className="fixed inset-0 bg-black/55 backdrop-blur-xs transition-opacity duration-300" 
        onClick={onClose} 
      />
      {/* Sidebar drawer container */}
      <div 
        className={cn(
          "relative flex w-full max-w-xs flex-col bg-card border-r border-border p-6 shadow-2xl transition-transform duration-300 ease-in-out h-full",
        )}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer transition-colors"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="flex-grow overflow-y-auto mt-6">
          {children}
        </div>
      </div>
    </div>
  );
}

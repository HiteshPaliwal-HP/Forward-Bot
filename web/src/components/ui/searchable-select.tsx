import React, { useState, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchableSelectOption {
  value: string;
  label: string;
  sublabel?: string;
}

interface SearchableSelectProps {
  options: SearchableSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
}

export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Select an option...",
  searchPlaceholder = "Search...",
  disabled = false,
  className,
  id,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  // Dropdown pixel position computed from trigger's bounding rect
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});

  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  );

  const filteredOptions = useMemo(() => {
    if (!search.trim()) return options;
    const term = search.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(term) ||
        (opt.sublabel && opt.sublabel.toLowerCase().includes(term))
    );
  }, [options, search]);

  // Recalculate dropdown position whenever it opens or window scrolls/resizes
  const recalcPosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    // Panel width: prefer 640px, but cap at viewport width with 16px margin
    const panelWidth = Math.min(640, window.innerWidth - 16);
    // Align right edge of panel with right edge of trigger; clamp left to 8px
    let left = rect.right - panelWidth;
    if (left < 8) left = 8;
    setDropdownStyle({
      position: "fixed",
      top: rect.bottom + 4,
      left,
      width: panelWidth,
      zIndex: 9999,
    });
  };

  useEffect(() => {
    if (isOpen) {
      recalcPosition();
      window.addEventListener("scroll", recalcPosition, true);
      window.addEventListener("resize", recalcPosition);
    }
    return () => {
      window.removeEventListener("scroll", recalcPosition, true);
      window.removeEventListener("resize", recalcPosition);
    };
  }, [isOpen]);

  // Focus search input when panel opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  // Close on outside click — covers both trigger and the portalled dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      const insideTrigger = triggerRef.current?.contains(target);
      const insideDropdown = dropdownRef.current?.contains(target);
      if (!insideTrigger && !insideDropdown) {
        setIsOpen(false);
        setSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (optValue: string) => {
    onChange(optValue);
    setIsOpen(false);
    setSearch("");
  };

  const handleToggle = () => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
      if (isOpen) setSearch("");
    }
  };

  const dropdownPanel = isOpen ? (
    <div
      ref={dropdownRef}
      style={{
        ...dropdownStyle,
        boxShadow: "0 10px 40px 0 rgba(0,0,0,0.35), 0 2px 8px 0 rgba(0,0,0,0.2)",
      }}
      className="bg-card border border-border rounded-md overflow-hidden"
    >
      {/* Search bar */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border bg-muted/20">
        <Search className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        <input
          ref={searchInputRef}
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={searchPlaceholder}
          className="flex-1 bg-transparent border-none outline-none text-xs font-medium text-foreground placeholder:text-muted-foreground"
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch("")}
            className="shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Option list */}
      <div className="overflow-y-auto max-h-72">
        {filteredOptions.length === 0 ? (
          <div className="px-3 py-4 text-xs text-center text-muted-foreground font-medium">
            No results found
          </div>
        ) : (
          filteredOptions.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleSelect(opt.value)}
                className={cn(
                  "w-full text-left px-4 py-2.5 flex flex-col gap-0.5 transition-colors cursor-pointer select-none",
                  isSelected
                    ? "bg-primary/10 text-primary"
                    : "text-foreground hover:bg-muted/40"
                )}
              >
                <span className={cn("text-xs font-semibold leading-tight", isSelected && "text-primary")}>
                  {opt.label}
                </span>
                {opt.sublabel && (
                  <span className="text-[10px] text-muted-foreground leading-snug opacity-80">
                    {opt.sublabel}
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  ) : null;

  return (
    <div className={cn("relative w-full", className)} id={id}>
      {/* Trigger button — same styling as existing <select> inputs */}
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={handleToggle}
        className={cn(
          "w-full h-10 px-3 border border-border rounded-md bg-card text-sm font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer focus:outline-none",
          isOpen && "border-primary ring-2 ring-primary/15",
          disabled && "opacity-50 cursor-not-allowed",
          selectedOption ? "text-foreground" : "text-muted-foreground"
        )}
      >
        <span className="truncate min-w-0">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={cn(
            "w-4 h-4 shrink-0 text-muted-foreground transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {/* Render dropdown via portal — escapes all overflow:hidden ancestors */}
      {typeof document !== "undefined" && createPortal(dropdownPanel, document.body)}
    </div>
  );
}

import { Clock, Shuffle, Image as ImageIcon, Key } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FilterConfig } from "@/types/ui";
import { Tooltip } from "./Tooltip";

const getDaysText = (days: string[]) => {
  const order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const sorted = [...days].sort((a, b) => {
    const idxA = order.indexOf(a.toLowerCase());
    const idxB = order.indexOf(b.toLowerCase());
    const valA = idxA === -1 ? 999 : idxA;
    const valB = idxB === -1 ? 999 : idxB;
    return valA - valB;
  });
  if (sorted.length === 5 && sorted[0].toLowerCase() === "mon" && sorted[4].toLowerCase() === "fri") {
    return "Mon–Fri";
  }
  if (sorted.length === 7) {
    return "Daily";
  }
  return sorted
    .map(d => {
      if (!d) return "";
      const clean = d.trim();
      return clean.charAt(0).toUpperCase() + clean.slice(1).toLowerCase().substring(0, 2);
    })
    .filter(Boolean)
    .join(", ");
};

const getOrdinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

interface FilterIconRowProps {
  config: FilterConfig;
}

export function FilterIconRow({ config }: FilterIconRowProps) {
  // 1. Time Window
  const hasTimeWindow = !!config.time_window;
  const timeWindowTitle = hasTimeWindow
    ? `${getDaysText(config.time_window!.days_of_week)} ${config.time_window!.start_time}–${config.time_window!.end_time} ${config.time_window!.timezone}`
    : "Time window: Inactive";

  // 2. Sampling
  const hasSampling = !!config.sampling && config.sampling.n > 0;
  const samplingTitle = hasSampling
    ? `Every ${getOrdinal(config.sampling!.n)} message`
    : "Sampling: Inactive";

  // 3. Media Type Filter
  const hasMediaType = !!config.media_type_filter && config.media_type_filter.length > 0;
  const mediaTypeTitle = hasMediaType
    ? config.media_type_filter!.join(", ")
    : "Media filter: Inactive";

  // 4. Keywords
  const blockCount = config.block_keywords?.length || 0;
  const allowCount = config.allow_keywords?.length || 0;
  const hasKeywords = blockCount > 0 || allowCount > 0;
  const keywordsTitle = hasKeywords
    ? `Keywords: ${blockCount} blocked, ${allowCount} allowed`
    : "Keywords: Inactive";

  const buttonClass = "w-6 h-6 flex items-center justify-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-all cursor-pointer";

  return (
    <div className="flex items-center gap-2 select-none">
      {/* Time Window Icon */}
      <Tooltip content={timeWindowTitle}>
        <button
          type="button"
          aria-label={`Time window filter. Status: ${hasTimeWindow ? "Active" : "Inactive"}. Config: ${timeWindowTitle}`}
          className={cn(
            buttonClass,
            hasTimeWindow ? "text-active opacity-100" : "text-secondary opacity-40"
          )}
        >
          <Clock className="w-4 h-4" />
        </button>
      </Tooltip>

      {/* Sampling Icon */}
      <Tooltip content={samplingTitle}>
        <button
          type="button"
          aria-label={`Sampling filter. Status: ${hasSampling ? "Active" : "Inactive"}. Config: ${samplingTitle}`}
          className={cn(
            buttonClass,
            hasSampling ? "text-active opacity-100" : "text-secondary opacity-40"
          )}
        >
          <Shuffle className="w-4 h-4" />
        </button>
      </Tooltip>

      {/* Media Type Icon */}
      <Tooltip content={mediaTypeTitle}>
        <button
          type="button"
          aria-label={`Media type filter. Status: ${hasMediaType ? "Active" : "Inactive"}. Config: ${mediaTypeTitle}`}
          className={cn(
            buttonClass,
            hasMediaType ? "text-active opacity-100" : "text-secondary opacity-40"
          )}
        >
          <ImageIcon className="w-4 h-4" />
        </button>
      </Tooltip>

      {/* Keywords Icon */}
      <Tooltip content={keywordsTitle}>
        <button
          type="button"
          aria-label={`Keyword filters. Status: ${hasKeywords ? "Active" : "Inactive"}. Config: ${keywordsTitle}`}
          className={cn(
            buttonClass,
            hasKeywords ? "text-active opacity-100" : "text-secondary opacity-40"
          )}
        >
          <Key className="w-4 h-4" />
        </button>
      </Tooltip>
    </div>
  );
}

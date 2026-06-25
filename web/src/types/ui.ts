export interface LogEntry {
  event: string;
  level: "debug" | "info" | "warning" | "error" | "critical";
  timestamp: string;
  correlation_id?: string;
  rule_id?: string;
  [key: string]: unknown;
}

export interface FilterConfig {
  time_window?: {
    timezone: string;
    days_of_week: string[];
    start_time: string;
    end_time: string;
  };
  sampling?: {
    n: number;
  };
  media_type_filter?: string[];
  block_keywords?: string[];
  allow_keywords?: string[];
}

export type StatusPillStatus = "active" | "inactive" | "error" | "stale";

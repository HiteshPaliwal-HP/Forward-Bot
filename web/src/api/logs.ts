import { apiClient } from "./client";
import type { LogEntry } from "@/types/ui";

export const SSE_STREAM_URL = "/api/v1/logs/stream";

export interface LogsRecentResponse {
  items: LogEntry[];
}

export interface LogsSearchResponse {
  items: LogEntry[];
}

export const logsApi = {
  fetchRecent: async (
    limit = 20,
    params?: { event?: string; correlation_id?: string }
  ): Promise<LogsRecentResponse> => {
    const { data } = await apiClient.get<LogsRecentResponse>("/logs/recent", {
      params: { limit, ...params },
    });
    return data;
  },

  searchLogs: async (params: {
    correlation_id: string;
    since?: string;
  }): Promise<LogsSearchResponse> => {
    const { data } = await apiClient.get<LogsSearchResponse>("/logs/search", {
      params,
    });
    return data;
  },
};

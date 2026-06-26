import { apiClient } from "./client";
import type { LogEntry } from "@/types/ui";

export interface LogsRecentResponse {
  items: LogEntry[];
}

export const logsApi = {
  fetchRecent: async (limit = 20): Promise<LogsRecentResponse> => {
    const { data } = await apiClient.get<LogsRecentResponse>("/logs/recent", {
      params: { limit },
    });
    return data;
  },
};

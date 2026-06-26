import { apiClient } from "./client";

export interface StatsSummary {
  forwarded_24h: number;
  failed_24h: number;
  blocked_24h: number;
  active_rules: number;
}

export const statsApi = {
  fetchSummary: async (): Promise<StatsSummary> => {
    const { data } = await apiClient.get<StatsSummary>("/stats/summary");
    return data;
  },
};

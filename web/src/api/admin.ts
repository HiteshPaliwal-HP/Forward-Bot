import { apiClient } from "./client";

export interface CacheRefreshResponse {
  version: number;
  rule_count: number;
  source_count: number;
  refreshed_at: string | null;
  status?: string;
  cache?: {
    version: number;
    rule_count: number;
    source_count: number;
    refreshed_at: string;
  };
}

export const adminApi = {
  refreshCache: async (): Promise<CacheRefreshResponse> => {
    const res = await apiClient.post<CacheRefreshResponse>("/admin/cache/refresh");
    return res.data;
  },
};

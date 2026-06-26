import { apiClient } from "./client";

export interface RulesListResponse {
  items: unknown[];
  total: number;
  page: number;
  page_size: number;
}

export const rulesApi = {
  fetchRules: async (params?: { page?: number; page_size?: number; is_active?: boolean }): Promise<RulesListResponse> => {
    const { data } = await apiClient.get<RulesListResponse>("/rules", { params });
    return data;
  },
};

import { apiClient } from "./client";

export interface SourceItem {
  id: string;
  telegram_id: number;
  telegram_username: string | null;
  display_name: string;
  type: "channel" | "group";
  folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourcesListResponse {
  items: SourceItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SourceCreatePayload {
  telegram_reference: string;  // Telegram username (@handle) or numeric ID
  display_name: string;
}

export interface SourceUpdatePayload {
  display_name: string;
  type: "channel" | "group";
  folder_id: string | null;
  telegram_username: string | null;
}

export interface SourcePatchPayload {
  display_name?: string;
  type?: "channel" | "group";
  folder_id?: string | null;
  telegram_username?: string | null;
}

export const sourcesApi = {
  fetchSources: async (params?: { page?: number; page_size?: number; folder_id?: string | null }): Promise<SourcesListResponse> => {
    const { data } = await apiClient.get<SourcesListResponse>("/sources", { params });
    return data;
  },

  fetchSource: async (id: string): Promise<SourceItem> => {
    const { data } = await apiClient.get<SourceItem>(`/sources/${id}`);
    return data;
  },

  createSource: async (payload: SourceCreatePayload): Promise<SourceItem> => {
    const { data } = await apiClient.post<SourceItem>("/sources", payload);
    return data;
  },

  updateSource: async (id: string, payload: SourceUpdatePayload): Promise<SourceItem> => {
    const { data } = await apiClient.put<SourceItem>(`/sources/${id}`, payload);
    return data;
  },

  patchSource: async (id: string, payload: SourcePatchPayload): Promise<SourceItem> => {
    const { data } = await apiClient.patch<SourceItem>(`/sources/${id}`, payload);
    return data;
  },

  deleteSource: async (id: string): Promise<void> => {
    await apiClient.delete(`/sources/${id}`);
  },
};

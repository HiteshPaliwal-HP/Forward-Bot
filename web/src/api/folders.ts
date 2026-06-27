import { apiClient } from "./client";
import type { SourceItem } from "./sources";

export interface FolderItem {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  source_count: number;
}

export interface FolderDetailsResponse extends FolderItem {
  sources: SourceItem[] | null;
}

export const foldersApi = {
  fetchFolders: async (params?: { name?: string }): Promise<FolderItem[]> => {
    const { data } = await apiClient.get<FolderItem[]>("/folders", { params });
    return data;
  },

  fetchFolder: async (id: string, params?: { include?: string }): Promise<FolderDetailsResponse> => {
    const { data } = await apiClient.get<FolderDetailsResponse>(`/folders/${id}`, { params });
    return data;
  },

  createFolder: async (payload: { name: string }): Promise<FolderItem> => {
    const { data } = await apiClient.post<FolderItem>("/folders", payload);
    return data;
  },

  renameFolder: async (id: string, payload: { name: string }): Promise<FolderItem> => {
    const { data } = await apiClient.put<FolderItem>(`/folders/${id}`, payload);
    return data;
  },

  deleteFolder: async (id: string): Promise<void> => {
    await apiClient.delete(`/folders/${id}`);
  },
};

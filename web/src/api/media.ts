import { apiClient } from "./client";

export const mediaApi = {
  fetchReplacementImages: async (): Promise<string[]> => {
    const { data } = await apiClient.get("/media/replacement-images");
    return data;
  },
};

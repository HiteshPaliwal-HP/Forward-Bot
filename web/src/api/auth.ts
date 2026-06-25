import { apiClient } from "./client";

export const authApi = {
  login: async (apiKey: string) => {
    const { data } = await apiClient.post("/auth/login", { api_key: apiKey });
    return data;
  },
  logout: async () => {
    const { data } = await apiClient.post("/auth/logout");
    return data;
  },
  me: async () => {
    const { data } = await apiClient.get("/auth/me");
    return data;
  },
};

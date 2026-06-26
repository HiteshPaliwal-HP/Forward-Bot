import axios from "axios";

export interface HealthResponse {
  status: string;
}

export interface ReadyResponse {
  mongodb: "up" | "down";
  cache: {
    version: number;
    refreshed_at: string;
  };
}

export interface TelegramStatusResponse {
  telegram: "connected" | "disconnected" | "reconnecting";
  last_event: string | null;
}

export const healthApi = {
  fetchTelegramStatus: async (): Promise<TelegramStatusResponse> => {
    const { data } = await axios.get<TelegramStatusResponse>("/health/telegram");
    return data;
  },
  fetchCacheStatus: async (): Promise<ReadyResponse> => {
    const { data } = await axios.get<ReadyResponse>("/health/ready");
    return data;
  },
  fetchHealth: async (): Promise<HealthResponse> => {
    const { data } = await axios.get<HealthResponse>("/health");
    return data;
  },
};


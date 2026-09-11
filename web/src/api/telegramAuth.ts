import { apiClient } from "./client";

export interface AuthStatus {
  connected: boolean;
  phone: string | null;
  phone_required: boolean;
  session_path: string;
}

export interface StartAuthPayload {
  phone?: string;
}

export interface VerifyAuthPayload {
  otp: string;
  password?: string;
  phone?: string;
}

export interface AuthResponse {
  status: string;
  message?: string;
  requires_2fa?: boolean;
}

export const telegramAuthApi = {
  getStatus: async (): Promise<AuthStatus> => {
    const res = await apiClient.get<AuthStatus>("/telegram/auth/status");
    return res.data;
  },

  startAuth: async (phone?: string): Promise<AuthResponse> => {
    const payload: StartAuthPayload = phone ? { phone } : {};
    const res = await apiClient.post<AuthResponse>("/telegram/auth/start", payload);
    return res.data;
  },

  verifyAuth: async (payload: VerifyAuthPayload): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/telegram/auth/verify", payload);
    return res.data;
  },

  terminateSession: async (): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/telegram/auth/terminate");
    return res.data;
  },
};

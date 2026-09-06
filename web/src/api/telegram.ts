import { apiClient } from "./client";

export interface TelegramDialog {
  id: string;
  name: string;
  username: string | null;
  is_channel: boolean;
  is_group: boolean;
}

export interface TelegramDialogsResponse {
  connected: boolean;
  dialogs: TelegramDialog[];
  error?: string;
}

export const telegramApi = {
  fetchDialogs: async (): Promise<TelegramDialogsResponse> => {
    const { data } = await apiClient.get<TelegramDialogsResponse>("/telegram/dialogs");
    return data;
  },
};

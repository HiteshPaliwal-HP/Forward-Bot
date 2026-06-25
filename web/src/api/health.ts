import axios from "axios";

export const healthApi = {
  fetchTelegramStatus: async () => {
    const { data } = await axios.get("/health/telegram");
    return data;
  },
  fetchCacheStatus: async () => {
    const { data } = await axios.get("/health/ready");
    return data;
  },
};

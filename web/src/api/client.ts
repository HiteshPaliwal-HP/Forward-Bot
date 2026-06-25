import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login if not already there, attaching the return parameter
      if (window.location.pathname !== "/login") {
        const currentPath = window.location.pathname + window.location.search;
        window.location.href = `/login?return=${encodeURIComponent(currentPath)}`;
      }
    }
    return Promise.reject(error);
  }
);

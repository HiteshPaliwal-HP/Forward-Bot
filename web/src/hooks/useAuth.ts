import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { queryKeys } from "@/lib/queryKeys";

export function useAuth() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: authApi.me,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  return {
    isAuthenticated: !!data?.ok,
    isLoading,
    error,
    refetch,
  };
}

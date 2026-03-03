import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createAnalysis, deleteAnalysis, getAnalysisStatus, getDashboard, listAnalyses } from "../../../api/client";

export function useAnalysesScreen() {
  const timezone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC", []);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["analyses"],
    queryFn: () => listAnalyses(20),
  });

  const createMutation = useMutation({
    mutationFn: (file: File) => createAnalysis(file, timezone),
    onSuccess: async (response) => {
      setAnalysisId(response.analysis_id);
      await queryClient.invalidateQueries({ queryKey: ["analyses"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAnalysis(id),
    onSuccess: async (_, id) => {
      if (analysisId === id) {
        setAnalysisId(null);
      }
      await queryClient.invalidateQueries({ queryKey: ["analyses"] });
    },
  });

  const statusQuery = useQuery({
    queryKey: ["analysis-status", analysisId],
    queryFn: () => getAnalysisStatus(analysisId as string),
    enabled: Boolean(analysisId),
    refetchInterval: (query) => {
      const current = query.state.data?.status;
      return current === "done" || current === "failed" ? false : 1500;
    },
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", analysisId],
    queryFn: () => getDashboard(analysisId as string),
    enabled: Boolean(analysisId) && statusQuery.data?.status === "done",
    staleTime: Infinity,
  });

  const error = createMutation.error || deleteMutation.error || statusQuery.error || dashboardQuery.error || listQuery.error;

  return {
    analysisId,
    setAnalysisId,
    listQuery,
    createMutation,
    deleteMutation,
    statusQuery,
    dashboardQuery,
    error,
  };
}

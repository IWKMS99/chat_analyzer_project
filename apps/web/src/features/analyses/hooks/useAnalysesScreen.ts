import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getListAnalysesQueryKey,
  useCreateAnalysis,
  useDeleteAnalysis,
  useGetAnalysisDashboard,
  useGetAnalysisStatus,
  useListAnalyses,
} from "@chat-analyzer/api-contracts";

interface UseAnalysesScreenOptions {
  analysisId: string | null;
  setAnalysisId: (analysisId: string | null) => void;
}

export function useAnalysesScreen({ analysisId, setAnalysisId }: UseAnalysesScreenOptions) {
  const timezone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC", []);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const listQuery = useListAnalyses({ limit: 20 });

  const createMutation = useCreateAnalysis({
    mutation: {
      onSuccess: async (response) => {
        setAnalysisId(response.analysis_id);
        await queryClient.invalidateQueries({ queryKey: getListAnalysesQueryKey() });
      },
    },
  });

  const deleteMutation = useDeleteAnalysis({
    mutation: {
      onSuccess: async (_, variables) => {
        if (analysisId === variables.analysisId) {
          setAnalysisId(null);
        }
        setPendingDeleteId(null);
        await queryClient.invalidateQueries({ queryKey: getListAnalysesQueryKey() });
      },
      onError: () => {
        setPendingDeleteId(null);
      },
    },
  });

  const statusQuery = useGetAnalysisStatus(analysisId ?? "", {
    query: {
      enabled: Boolean(analysisId),
      refetchInterval: (query) => {
        const current = query.state.data?.status;
        return current === "done" || current === "failed" ? false : 1500;
      },
    },
  });

  const dashboardQuery = useGetAnalysisDashboard(analysisId ?? "", {
    query: {
      enabled: Boolean(analysisId) && statusQuery.data?.status === "done",
      staleTime: Infinity,
    },
  });

  const startAnalysis = (file: File) =>
    createMutation.mutate({
      data: {
        file,
        timezone,
      },
    });

  const removeAnalysis = (id: string) => {
    setPendingDeleteId(id);
    deleteMutation.mutate({ analysisId: id });
  };

  const error = createMutation.error || deleteMutation.error || statusQuery.error || dashboardQuery.error || listQuery.error;

  return {
    analysisId,
    setAnalysisId,
    listQuery,
    createMutation,
    deleteMutation,
    statusQuery,
    dashboardQuery,
    startAnalysis,
    removeAnalysis,
    pendingDeleteId,
    error,
  };
}

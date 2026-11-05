import { useCallback, useState } from "react";

type OptimizationGoal =
  | "profit-factor"
  | "win-rate"
  | "sharpe"
  | "drawdown"
  | "balanced";

export interface OptimizationParams {
  strategy: string;
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  optimizationGoal: OptimizationGoal;
  model?: string;
}

interface OptimizationResult {
  id: string;
  status: string;
  progress?: number;
}

interface UseOptimizerState {
  isOptimizing: boolean;
  progress: number;
  activeOptimization: OptimizationResult | null;
  error: string | null;
}

export function useOptimizer() {
  const [state, setState] = useState<UseOptimizerState>({
    isOptimizing: false,
    progress: 0,
    activeOptimization: null,
    error: null,
  });

  const startOptimization = useCallback(async (params: OptimizationParams) => {
    try {
      setState({
        isOptimizing: true,
        progress: 0,
        activeOptimization: null,
        error: null,
      });

      const response = await fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: params.strategy,
          parameters: {},
          timeframe: params.timeframe,
          symbol: params.symbol,
          startDate: params.startDate,
          endDate: params.endDate,
          optimizationGoal: params.optimizationGoal,
          model: params.model,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start optimization");
      }

      const data = (await response.json()) as {
        optimizationId: string;
      };

      // Single status fetch based on mocked API
      const statusResponse = await fetch(
        `/api/optimize/status/${data.optimizationId}`,
      );
      if (!statusResponse.ok) {
        throw new Error("Failed to get optimization status");
      }

      const statusJson = (await statusResponse.json()) as {
        data: { id: string; status: string; progress: number };
      };

      setState({
        isOptimizing: statusJson.data.status !== "completed",
        progress: statusJson.data.progress,
        activeOptimization: statusJson.data,
        error: null,
      });
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isOptimizing: false,
        error:
          error instanceof Error ? error.message : "Optimization request failed",
      }));
    }
  }, []);

  return {
    ...state,
    startOptimization,
  };
}


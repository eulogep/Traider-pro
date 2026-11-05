import { useCallback, useState } from "react";
import type { BacktestResult } from "@shared/types/trading";

export interface BacktestParams {
  strategy: string;
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  initialBalance: number;
  riskPerTrade: number;
}

interface UseBacktestState {
  isRunning: boolean;
  progress: number;
  result: BacktestResult | null;
  error: string | null;
}

export function useBacktest() {
  const [state, setState] = useState<UseBacktestState>({
    isRunning: false,
    progress: 0,
    result: null,
    error: null,
  });

  const startBacktest = useCallback(async (params: BacktestParams) => {
    try {
      setState({ isRunning: true, progress: 0, result: null, error: null });

      const response = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: params.strategy,
          parameters: {},
          symbol: params.symbol,
          timeframe: params.timeframe,
          startDate: params.startDate,
          endDate: params.endDate,
          initialBalance: params.initialBalance,
          riskPerTrade: params.riskPerTrade,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start backtest");
      }

      const data = (await response.json()) as {
        backtestId: string;
      };

      // Poll for results using the mocked /api/backtest/:id endpoint
      const resultResponse = await fetch(`/api/backtest/${data.backtestId}`);
      if (!resultResponse.ok) {
        throw new Error("Failed to fetch backtest results");
      }

      const resultJson = (await resultResponse.json()) as {
        data: BacktestResult;
      };

      setState({
        isRunning: false,
        progress: 100,
        result: resultJson.data,
        error: null,
      });
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isRunning: false,
        error: error instanceof Error ? error.message : "Backtest failed",
      }));
    }
  }, []);

  return {
    ...state,
    startBacktest,
  };
}


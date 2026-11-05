import { useCallback } from "react";
import { useMT5 } from "@/hooks/useMT5";
import type { MT5Position } from "@/lib/mt5Service";

export interface RiskSummary {
  totalExposure: number;
  positionsCount: number;
  averagePositionSize: number;
}

export function useTrading() {
  const { positions, account, placeOrder, closePosition, connected, error } =
    useMT5();

  const riskSummary: RiskSummary = {
    totalExposure: positions.reduce(
      (acc, position) => acc + position.volume,
      0,
    ),
    positionsCount: positions.length,
    averagePositionSize:
      positions.length > 0
        ? positions.reduce(
            (acc, position) => acc + position.volume,
            0,
          ) / positions.length
        : 0,
  };

  const closeAllPositions = useCallback(async () => {
    const tickets = positions.map((p: MT5Position) => p.ticket);
    // Close sequentially to keep it simple for now
    for (const ticket of tickets) {
      // eslint-disable-next-line no-await-in-loop
      await closePosition(ticket);
    }
  }, [positions, closePosition]);

  return {
    connected,
    account,
    positions,
    placeOrder,
    closePosition,
    closeAllPositions,
    riskSummary,
    error,
  };
}


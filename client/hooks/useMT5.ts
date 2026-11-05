import { useMT5Store } from "@/lib/mt5Store";

export function useMT5() {
  return useMT5Store();
}

// Hook for specific symbol data
export function useMT5Symbol(symbol: string) {
  const { symbols, connected } = useMT5Store();
  const symbolData = symbols.find((s) => s.symbol === symbol);

  return {
    symbol: symbolData,
    connected,
    isLoading: connected && !symbolData,
  };
}

// Hook for account summary
export function useMT5Account() {
  const { account, connected, positions } = useMT5Store();

  const summary = {
    balance: account?.balance || 0,
    equity: account?.equity || 0,
    margin: account?.margin || 0,
    freeMargin: account?.freeMargin || 0,
    marginLevel: account?.marginLevel || 0,
    profit: account?.profit || 0,
    openPositions: positions.length,
    currency: account?.currency || "USD",
  };

  return {
    account,
    summary,
    connected,
  };
}

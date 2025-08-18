import { useState, useEffect, useCallback } from "react";
import {
  mt5Service,
  MT5AccountInfo,
  MT5Symbol,
  MT5Position,
  MT5Order,
  MT5Trade,
  MT5ConnectionConfig,
} from "@/lib/mt5Service";

export interface MT5State {
  connected: boolean;
  connecting: boolean;
  account: MT5AccountInfo | null;
  symbols: MT5Symbol[];
  positions: MT5Position[];
  orders: MT5Order[];
  tradeHistory: MT5Trade[];
  error: string | null;
}

export function useMT5() {
  const [state, setState] = useState<MT5State>({
    connected: false,
    connecting: false,
    account: null,
    symbols: [],
    positions: [],
    orders: [],
    tradeHistory: [],
    error: null,
  });

  // Connection management
  const connect = useCallback(async (config: MT5ConnectionConfig) => {
    setState((prev) => ({ ...prev, connecting: true, error: null }));

    try {
      const success = await mt5Service.connect(config);
      if (success) {
        setState((prev) => ({
          ...prev,
          connected: true,
          connecting: false,
          account: mt5Service.getAccountInfo(),
          symbols: mt5Service.getSymbols(),
          positions: mt5Service.getPositions(),
          orders: mt5Service.getOrders(),
          tradeHistory: mt5Service.getTradeHistory(50),
        }));
      } else {
        setState((prev) => ({
          ...prev,
          connecting: false,
          error: "Failed to connect to MT5",
        }));
      }
    } catch (error) {
      setState((prev) => ({
        ...prev,
        connecting: false,
        error: error instanceof Error ? error.message : "Connection failed",
      }));
    }
  }, []);

  const disconnect = useCallback(() => {
    mt5Service.disconnect();
    setState({
      connected: false,
      connecting: false,
      account: null,
      symbols: [],
      positions: [],
      orders: [],
      tradeHistory: [],
      error: null,
    });
  }, []);

  // Trading operations
  const placeOrder = useCallback(async (order: any) => {
    try {
      const ticket = await mt5Service.placeMarketOrder(order);
      // Refresh positions
      setState((prev) => ({
        ...prev,
        positions: mt5Service.getPositions(),
        account: mt5Service.getAccountInfo(),
      }));
      return ticket;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Order failed",
      }));
      throw error;
    }
  }, []);

  const closePosition = useCallback(async (ticket: number) => {
    try {
      await mt5Service.closePosition(ticket);
      setState((prev) => ({
        ...prev,
        positions: mt5Service.getPositions(),
        tradeHistory: mt5Service.getTradeHistory(50),
        account: mt5Service.getAccountInfo(),
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Close position failed",
      }));
      throw error;
    }
  }, []);

  const placePendingOrder = useCallback(async (order: any) => {
    try {
      const ticket = await mt5Service.placePendingOrder(order);
      setState((prev) => ({
        ...prev,
        orders: mt5Service.getOrders(),
      }));
      return ticket;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Pending order failed",
      }));
      throw error;
    }
  }, []);

  const deleteOrder = useCallback(async (ticket: number) => {
    try {
      await mt5Service.deleteOrder(ticket);
      setState((prev) => ({
        ...prev,
        orders: mt5Service.getOrders(),
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Delete order failed",
      }));
      throw error;
    }
  }, []);

  // Real-time updates subscription
  useEffect(() => {
    const unsubscribe = mt5Service.subscribe((data) => {
      switch (data.type) {
        case "connection":
          if (data.status === "connected") {
            setState((prev) => ({
              ...prev,
              connected: true,
              account: data.account,
              symbols: mt5Service.getSymbols(),
              positions: mt5Service.getPositions(),
              orders: mt5Service.getOrders(),
              tradeHistory: mt5Service.getTradeHistory(50),
            }));
          } else if (data.status === "disconnected") {
            setState((prev) => ({
              ...prev,
              connected: false,
              account: null,
              symbols: [],
              positions: [],
              orders: [],
              tradeHistory: [],
            }));
          } else if (data.status === "error") {
            setState((prev) => ({
              ...prev,
              error: data.error?.message || "Connection error",
            }));
          }
          break;

        case "price_update":
          setState((prev) => ({
            ...prev,
            symbols: data.symbols,
            account: data.account,
            positions: mt5Service.getPositions(), // Update positions with new profits
          }));
          break;

        case "order_executed":
          setState((prev) => ({
            ...prev,
            positions: mt5Service.getPositions(),
            account: mt5Service.getAccountInfo(),
          }));
          break;

        case "position_closed":
          setState((prev) => ({
            ...prev,
            positions: mt5Service.getPositions(),
            tradeHistory: mt5Service.getTradeHistory(50),
            account: mt5Service.getAccountInfo(),
          }));
          break;

        case "order_placed":
          setState((prev) => ({
            ...prev,
            orders: mt5Service.getOrders(),
          }));
          break;

        case "order_deleted":
          setState((prev) => ({
            ...prev,
            orders: mt5Service.getOrders(),
          }));
          break;
      }
    });

    // Check if already connected
    if (mt5Service.isConnected()) {
      setState((prev) => ({
        ...prev,
        connected: true,
        account: mt5Service.getAccountInfo(),
        symbols: mt5Service.getSymbols(),
        positions: mt5Service.getPositions(),
        orders: mt5Service.getOrders(),
        tradeHistory: mt5Service.getTradeHistory(50),
      }));
    }

    return unsubscribe;
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    placeOrder,
    closePosition,
    placePendingOrder,
    deleteOrder,
    clearError: useCallback(
      () => setState((prev) => ({ ...prev, error: null })),
      [],
    ),
  };
}

// Hook for specific symbol data
export function useMT5Symbol(symbol: string) {
  const { symbols, connected } = useMT5();
  const symbolData = symbols.find((s) => s.symbol === symbol);

  return {
    symbol: symbolData,
    connected,
    isLoading: connected && !symbolData,
  };
}

// Hook for account summary
export function useMT5Account() {
  const { account, connected, positions } = useMT5();

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

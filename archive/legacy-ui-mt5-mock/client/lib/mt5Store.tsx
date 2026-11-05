import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  type ReactNode,
} from "react";
import {
  mt5Service,
  type MT5AccountInfo,
  type MT5Symbol,
  type MT5Position,
  type MT5Order,
  type MT5Trade,
  type MT5ConnectionConfig,
  type MarketOrder,
  type PendingOrder,
} from "@/lib/mt5Service";

type MT5ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

interface MT5StoreState {
  status: MT5ConnectionStatus;
  connected: boolean;
  connecting: boolean;
  account: MT5AccountInfo | null;
  symbols: MT5Symbol[];
  positions: MT5Position[];
  orders: MT5Order[];
  tradeHistory: MT5Trade[];
  error: string | null;
}

const initialState: MT5StoreState = {
  status: "disconnected",
  connected: false,
  connecting: false,
  account: null,
  symbols: [],
  positions: [],
  orders: [],
  tradeHistory: [],
  error: null,
};

type MT5Action =
  | { type: "CONNECT_START" }
  | {
      type: "CONNECT_SUCCESS";
      payload: {
        account: MT5AccountInfo | null;
        symbols: MT5Symbol[];
        positions: MT5Position[];
        orders: MT5Order[];
        tradeHistory: MT5Trade[];
      };
    }
  | { type: "CONNECT_ERROR"; error: string }
  | { type: "DISCONNECT" }
  | {
      type: "PRICE_UPDATE";
      payload: {
        symbols: MT5Symbol[];
        account: MT5AccountInfo | null;
      };
    }
  | {
      type: "REFRESH_STATE";
      payload: {
        account: MT5AccountInfo | null;
        positions: MT5Position[];
        orders: MT5Order[];
        tradeHistory: MT5Trade[];
      };
    }
  | { type: "CLEAR_ERROR" };

function mt5Reducer(state: MT5StoreState, action: MT5Action): MT5StoreState {
  switch (action.type) {
    case "CONNECT_START":
      return {
        ...state,
        status: "connecting",
        connected: false,
        connecting: true,
        error: null,
      };

    case "CONNECT_SUCCESS":
      return {
        ...state,
        status: "connected",
        connected: true,
        connecting: false,
        account: action.payload.account,
        symbols: action.payload.symbols,
        positions: action.payload.positions,
        orders: action.payload.orders,
        tradeHistory: action.payload.tradeHistory,
        error: null,
      };

    case "CONNECT_ERROR":
      return {
        ...state,
        status: "disconnected",
        connected: false,
        connecting: false,
        error: action.error,
      };

    case "DISCONNECT":
      return {
        ...initialState,
        status: "disconnected",
      };

    case "PRICE_UPDATE":
      return {
        ...state,
        symbols: action.payload.symbols,
        account: action.payload.account,
      };

    case "REFRESH_STATE":
      return {
        ...state,
        account: action.payload.account,
        positions: action.payload.positions,
        orders: action.payload.orders,
        tradeHistory: action.payload.tradeHistory,
      };

    case "CLEAR_ERROR":
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

interface MT5StoreContextValue extends MT5StoreState {
  connect: (config: MT5ConnectionConfig) => Promise<void>;
  disconnect: () => void;
  placeOrder: (order: MarketOrder) => Promise<number | null>;
  closePosition: (ticket: number) => Promise<void>;
  placePendingOrder: (order: PendingOrder) => Promise<number | null>;
  deleteOrder: (ticket: number) => Promise<void>;
  clearError: () => void;
}

const MT5StoreContext = createContext<MT5StoreContextValue | undefined>(
  undefined,
);

export function MT5Provider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(mt5Reducer, initialState);

  const connect = useCallback(async (config: MT5ConnectionConfig) => {
    dispatch({ type: "CONNECT_START" });

    try {
      const success = await mt5Service.connect(config);
      if (!success) {
        dispatch({
          type: "CONNECT_ERROR",
          error: "Failed to connect to MT5",
        });
        return;
      }

      dispatch({
        type: "CONNECT_SUCCESS",
        payload: {
          account: mt5Service.getAccountInfo(),
          symbols: mt5Service.getSymbols(),
          positions: mt5Service.getPositions(),
          orders: mt5Service.getOrders(),
          tradeHistory: mt5Service.getTradeHistory(50),
        },
      });
    } catch (error) {
      dispatch({
        type: "CONNECT_ERROR",
        error:
          error instanceof Error ? error.message : "Failed to connect to MT5",
      });
    }
  }, []);

  const disconnect = useCallback(() => {
    mt5Service.disconnect();
    dispatch({ type: "DISCONNECT" });
  }, []);

  const placeOrder = useCallback(
    async (order: MarketOrder) => {
      try {
        const ticket = await mt5Service.placeMarketOrder(order);
        dispatch({
          type: "REFRESH_STATE",
          payload: {
            account: mt5Service.getAccountInfo(),
            positions: mt5Service.getPositions(),
            orders: mt5Service.getOrders(),
            tradeHistory: mt5Service.getTradeHistory(50),
          },
        });
        return ticket;
      } catch (error) {
        dispatch({
          type: "CONNECT_ERROR",
          error: error instanceof Error ? error.message : "Order failed",
        });
        throw error;
      }
    },
    [],
  );

  const closePosition = useCallback(async (ticket: number) => {
    try {
      await mt5Service.closePosition(ticket);
      dispatch({
        type: "REFRESH_STATE",
        payload: {
          account: mt5Service.getAccountInfo(),
          positions: mt5Service.getPositions(),
          orders: mt5Service.getOrders(),
          tradeHistory: mt5Service.getTradeHistory(50),
        },
      });
    } catch (error) {
      dispatch({
        type: "CONNECT_ERROR",
        error:
          error instanceof Error ? error.message : "Close position failed",
      });
      throw error;
    }
  }, []);

  const placePendingOrder = useCallback(
    async (order: PendingOrder) => {
      try {
        const ticket = await mt5Service.placePendingOrder(order);
        dispatch({
          type: "REFRESH_STATE",
          payload: {
            account: mt5Service.getAccountInfo(),
            positions: mt5Service.getPositions(),
            orders: mt5Service.getOrders(),
            tradeHistory: mt5Service.getTradeHistory(50),
          },
        });
        return ticket;
      } catch (error) {
        dispatch({
          type: "CONNECT_ERROR",
          error:
            error instanceof Error ? error.message : "Pending order failed",
        });
        throw error;
      }
    },
    [],
  );

  const deleteOrder = useCallback(async (ticket: number) => {
    try {
      await mt5Service.deleteOrder(ticket);
      dispatch({
        type: "REFRESH_STATE",
        payload: {
          account: mt5Service.getAccountInfo(),
          positions: mt5Service.getPositions(),
          orders: mt5Service.getOrders(),
          tradeHistory: mt5Service.getTradeHistory(50),
        },
      });
    } catch (error) {
      dispatch({
        type: "CONNECT_ERROR",
        error:
          error instanceof Error ? error.message : "Delete order failed",
      });
      throw error;
    }
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
  }, []);

  // Subscribe to real-time updates from mt5Service
  useEffect(() => {
    const unsubscribe = mt5Service.subscribe((rawData) => {
      if (
        !rawData ||
        typeof rawData !== "object" ||
        !("type" in rawData)
      ) {
        return;
      }

      const data = rawData as {
        type: string;
        status?: string;
        account?: MT5AccountInfo | null;
        symbols?: MT5Symbol[];
        error?: { message?: string };
      };

      switch (data.type) {
        case "connection":
          if (data.status === "connected") {
            dispatch({
              type: "CONNECT_SUCCESS",
              payload: {
                account: data.account ?? mt5Service.getAccountInfo(),
                symbols: mt5Service.getSymbols(),
                positions: mt5Service.getPositions(),
                orders: mt5Service.getOrders(),
                tradeHistory: mt5Service.getTradeHistory(50),
              },
            });
          } else if (data.status === "disconnected") {
            dispatch({ type: "DISCONNECT" });
          } else if (data.status === "error") {
            dispatch({
              type: "CONNECT_ERROR",
              error: data.error?.message || "Connection error",
            });
          }
          break;

        case "price_update":
          dispatch({
            type: "PRICE_UPDATE",
            payload: {
              symbols: data.symbols ?? mt5Service.getSymbols(),
              account: data.account ?? mt5Service.getAccountInfo(),
            },
          });
          break;

        case "order_executed":
        case "position_closed":
        case "order_placed":
        case "order_deleted":
          dispatch({
            type: "REFRESH_STATE",
            payload: {
              account: mt5Service.getAccountInfo(),
              positions: mt5Service.getPositions(),
              orders: mt5Service.getOrders(),
              tradeHistory: mt5Service.getTradeHistory(50),
            },
          });
          break;
      }
    });

    // Initialize from existing connection if already connected
    if (mt5Service.isConnected()) {
      dispatch({
        type: "CONNECT_SUCCESS",
        payload: {
          account: mt5Service.getAccountInfo(),
          symbols: mt5Service.getSymbols(),
          positions: mt5Service.getPositions(),
          orders: mt5Service.getOrders(),
          tradeHistory: mt5Service.getTradeHistory(50),
        },
      });
    }

    return unsubscribe;
  }, []);

  const value: MT5StoreContextValue = {
    ...state,
    connect,
    disconnect,
    placeOrder,
    closePosition,
    placePendingOrder,
    deleteOrder,
    clearError,
  };

  return (
    <MT5StoreContext.Provider value={value}>
      {children}
    </MT5StoreContext.Provider>
  );
}

export function useMT5Store(): MT5StoreContextValue {
  const context = useContext(MT5StoreContext);
  if (!context) {
    throw new Error("useMT5Store must be used within an MT5Provider");
  }
  return context;
}


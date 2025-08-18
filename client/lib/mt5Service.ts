// MT5 Service - Manages MetaTrader 5 integration
// In production, this would connect to actual MT5 terminals via Python bridge or direct API

export interface MT5ConnectionConfig {
  server: string;
  login: string;
  password: string;
  path?: string;
  timeout?: number;
}

export interface MT5AccountInfo {
  login: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  profit: number;
  currency: string;
  company: string;
  name: string;
  server: string;
}

export interface MT5Symbol {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  time: number;
  spread: number;
  digits: number;
  change: number;
  changePercent: number;
}

export interface MT5Position {
  ticket: number;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  openPrice: number;
  currentPrice: number;
  profit: number;
  swap: number;
  comment: string;
  openTime: number;
  sl: number;
  tp: number;
}

export interface MT5Order {
  ticket: number;
  symbol: string;
  type: "BUY_LIMIT" | "SELL_LIMIT" | "BUY_STOP" | "SELL_STOP";
  volume: number;
  price: number;
  sl: number;
  tp: number;
  comment: string;
  time: number;
}

export interface MT5Trade {
  ticket: number;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  openPrice: number;
  closePrice?: number;
  profit: number;
  commission: number;
  swap: number;
  openTime: number;
  closeTime?: number;
  comment: string;
  sl: number;
  tp: number;
}

export interface MarketOrder {
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  sl?: number;
  tp?: number;
  comment?: string;
}

export interface PendingOrder {
  symbol: string;
  type: "BUY_LIMIT" | "SELL_LIMIT" | "BUY_STOP" | "SELL_STOP";
  volume: number;
  price: number;
  sl?: number;
  tp?: number;
  comment?: string;
}

export class MT5Service {
  private static instance: MT5Service;
  private connected = false;
  private connectionConfig: MT5ConnectionConfig | null = null;
  private accountInfo: MT5AccountInfo | null = null;
  private symbols: Map<string, MT5Symbol> = new Map();
  private positions: MT5Position[] = [];
  private orders: MT5Order[] = [];
  private tradeHistory: MT5Trade[] = [];
  private subscribers: Set<(data: any) => void> = new Set();
  private priceUpdateInterval: number | null = null;

  private constructor() {
    this.initializeMockData();
  }

  public static getInstance(): MT5Service {
    if (!MT5Service.instance) {
      MT5Service.instance = new MT5Service();
    }
    return MT5Service.instance;
  }

  // Connection Management
  async connect(config: MT5ConnectionConfig): Promise<boolean> {
    try {
      // Simulate connection process
      console.log("Connecting to MT5 server:", config.server);

      // In production, this would make actual MT5 API calls
      await new Promise((resolve) => setTimeout(resolve, 2000));

      this.connectionConfig = config;
      this.connected = true;

      // Initialize account info
      this.accountInfo = {
        login: config.login,
        balance: 50000.0,
        equity: 52340.5,
        margin: 1250.0,
        freeMargin: 51090.5,
        marginLevel: 4187.24,
        profit: 2340.5,
        currency: "USD",
        company: "MetaQuotes Software Corp.",
        name: "John Trader",
        server: config.server,
      };

      // Start real-time data feed
      this.startPriceFeed();

      this.notifySubscribers({
        type: "connection",
        status: "connected",
        account: this.accountInfo,
      });
      return true;
    } catch (error) {
      console.error("Failed to connect to MT5:", error);
      this.connected = false;
      this.notifySubscribers({ type: "connection", status: "error", error });
      return false;
    }
  }

  disconnect(): void {
    this.connected = false;
    this.connectionConfig = null;
    this.accountInfo = null;
    this.stopPriceFeed();
    this.notifySubscribers({ type: "connection", status: "disconnected" });
  }

  isConnected(): boolean {
    return this.connected;
  }

  getAccountInfo(): MT5AccountInfo | null {
    return this.accountInfo;
  }

  // Market Data
  getSymbols(): MT5Symbol[] {
    return Array.from(this.symbols.values());
  }

  getSymbol(symbol: string): MT5Symbol | undefined {
    return this.symbols.get(symbol);
  }

  // Position Management
  getPositions(): MT5Position[] {
    return this.positions;
  }

  getPosition(ticket: number): MT5Position | undefined {
    return this.positions.find((pos) => pos.ticket === ticket);
  }

  // Order Management
  getOrders(): MT5Order[] {
    return this.orders;
  }

  async placeMarketOrder(order: MarketOrder): Promise<number | null> {
    if (!this.connected) {
      throw new Error("Not connected to MT5");
    }

    const symbol = this.symbols.get(order.symbol);
    if (!symbol) {
      throw new Error(`Symbol ${order.symbol} not found`);
    }

    // Simulate order execution
    const ticket = Date.now() + Math.floor(Math.random() * 1000);
    const executionPrice = order.type === "BUY" ? symbol.ask : symbol.bid;

    const position: MT5Position = {
      ticket,
      symbol: order.symbol,
      type: order.type,
      volume: order.volume,
      openPrice: executionPrice,
      currentPrice: executionPrice,
      profit: 0,
      swap: 0,
      comment: order.comment || "",
      openTime: Date.now(),
      sl: order.sl || 0,
      tp: order.tp || 0,
    };

    this.positions.push(position);

    // Update account balance (simulate commission)
    if (this.accountInfo) {
      this.accountInfo.margin += order.volume * 100; // Simplified margin calculation
      this.accountInfo.freeMargin =
        this.accountInfo.equity - this.accountInfo.margin;
    }

    this.notifySubscribers({ type: "order_executed", order: position });
    return ticket;
  }

  async placePendingOrder(order: PendingOrder): Promise<number | null> {
    if (!this.connected) {
      throw new Error("Not connected to MT5");
    }

    const ticket = Date.now() + Math.floor(Math.random() * 1000);

    const pendingOrder: MT5Order = {
      ticket,
      symbol: order.symbol,
      type: order.type,
      volume: order.volume,
      price: order.price,
      sl: order.sl || 0,
      tp: order.tp || 0,
      comment: order.comment || "",
      time: Date.now(),
    };

    this.orders.push(pendingOrder);
    this.notifySubscribers({ type: "order_placed", order: pendingOrder });
    return ticket;
  }

  async closePosition(ticket: number): Promise<boolean> {
    if (!this.connected) {
      throw new Error("Not connected to MT5");
    }

    const positionIndex = this.positions.findIndex(
      (pos) => pos.ticket === ticket,
    );
    if (positionIndex === -1) {
      throw new Error(`Position ${ticket} not found`);
    }

    const position = this.positions[positionIndex];
    const symbol = this.symbols.get(position.symbol);
    if (!symbol) {
      throw new Error(`Symbol ${position.symbol} not found`);
    }

    // Calculate final profit
    const closePrice = position.type === "BUY" ? symbol.bid : symbol.ask;
    const profit =
      position.type === "BUY"
        ? (closePrice - position.openPrice) * position.volume * 100
        : (position.openPrice - closePrice) * position.volume * 100;

    // Create trade history record
    const trade: MT5Trade = {
      ticket: position.ticket,
      symbol: position.symbol,
      type: position.type,
      volume: position.volume,
      openPrice: position.openPrice,
      closePrice,
      profit,
      commission: -7.5, // Simulated commission
      swap: position.swap,
      openTime: position.openTime,
      closeTime: Date.now(),
      comment: position.comment,
      sl: position.sl,
      tp: position.tp,
    };

    this.tradeHistory.unshift(trade);
    this.positions.splice(positionIndex, 1);

    // Update account info
    if (this.accountInfo) {
      this.accountInfo.balance += profit - 7.5;
      this.accountInfo.equity =
        this.accountInfo.balance + this.calculateOpenProfit();
      this.accountInfo.margin -= position.volume * 100;
      this.accountInfo.freeMargin =
        this.accountInfo.equity - this.accountInfo.margin;
      this.accountInfo.profit = this.calculateOpenProfit();
    }

    this.notifySubscribers({ type: "position_closed", trade });
    return true;
  }

  async deleteOrder(ticket: number): Promise<boolean> {
    if (!this.connected) {
      throw new Error("Not connected to MT5");
    }

    const orderIndex = this.orders.findIndex(
      (order) => order.ticket === ticket,
    );
    if (orderIndex === -1) {
      throw new Error(`Order ${ticket} not found`);
    }

    this.orders.splice(orderIndex, 1);
    this.notifySubscribers({ type: "order_deleted", ticket });
    return true;
  }

  // Trade History
  getTradeHistory(limit?: number): MT5Trade[] {
    return limit ? this.tradeHistory.slice(0, limit) : this.tradeHistory;
  }

  // Subscription Management
  subscribe(callback: (data: any) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  private notifySubscribers(data: any): void {
    this.subscribers.forEach((callback) => callback(data));
  }

  // Private Methods
  private initializeMockData(): void {
    // Initialize popular trading symbols with realistic data
    const symbolData = [
      {
        symbol: "XAUUSD",
        bid: 1985.45,
        ask: 1985.65,
        volume: 156234,
        change: 12.8,
      },
      {
        symbol: "EURUSD",
        bid: 1.0875,
        ask: 1.0876,
        volume: 892456,
        change: -0.0023,
      },
      {
        symbol: "GBPUSD",
        bid: 1.2634,
        ask: 1.2636,
        volume: 445678,
        change: 0.0045,
      },
      {
        symbol: "USDJPY",
        bid: 149.82,
        ask: 149.84,
        volume: 678923,
        change: -0.34,
      },
      {
        symbol: "USDCHF",
        bid: 0.8945,
        ask: 0.8947,
        volume: 234567,
        change: 0.0012,
      },
      {
        symbol: "AUDUSD",
        bid: 0.6523,
        ask: 0.6525,
        volume: 345678,
        change: 0.0034,
      },
    ];

    symbolData.forEach((data) => {
      const symbol: MT5Symbol = {
        symbol: data.symbol,
        bid: data.bid,
        ask: data.ask,
        last: data.bid,
        volume: data.volume,
        time: Date.now(),
        spread: Math.round((data.ask - data.bid) * Math.pow(10, 5)),
        digits: data.symbol === "USDJPY" ? 3 : 5,
        change: data.change,
        changePercent: (data.change / data.bid) * 100,
      };
      this.symbols.set(data.symbol, symbol);
    });

    // Initialize some mock trade history
    this.initializeMockHistory();
  }

  private initializeMockHistory(): void {
    const mockTrades: MT5Trade[] = [
      {
        ticket: 12345,
        symbol: "XAUUSD",
        type: "BUY",
        volume: 0.1,
        openPrice: 1980.5,
        closePrice: 1985.45,
        profit: 495.0,
        commission: -7.5,
        swap: 0,
        openTime: Date.now() - 3600000,
        closeTime: Date.now() - 1800000,
        comment: "AI Signal",
        sl: 1975.0,
        tp: 1990.0,
      },
      {
        ticket: 12344,
        symbol: "EURUSD",
        type: "SELL",
        volume: 0.5,
        openPrice: 1.089,
        closePrice: 1.0875,
        profit: 750.0,
        commission: -7.5,
        swap: -2.5,
        openTime: Date.now() - 7200000,
        closeTime: Date.now() - 3600000,
        comment: "Pullback Strategy",
        sl: 1.091,
        tp: 1.086,
      },
    ];

    this.tradeHistory.push(...mockTrades);
  }

  private startPriceFeed(): void {
    if (this.priceUpdateInterval) {
      clearInterval(this.priceUpdateInterval);
    }

    this.priceUpdateInterval = window.setInterval(() => {
      this.updatePrices();
    }, 1000); // Update every second
  }

  private stopPriceFeed(): void {
    if (this.priceUpdateInterval) {
      clearInterval(this.priceUpdateInterval);
      this.priceUpdateInterval = null;
    }
  }

  private updatePrices(): void {
    this.symbols.forEach((symbol, key) => {
      // Simulate realistic price movement
      const volatility = 0.0001; // 0.01% volatility
      const change = (Math.random() - 0.5) * 2 * volatility * symbol.bid;

      symbol.bid += change;
      symbol.ask = symbol.bid + (symbol.ask - symbol.bid); // Maintain spread
      symbol.last = symbol.bid;
      symbol.time = Date.now();
      symbol.change += change;
      symbol.changePercent = (symbol.change / symbol.bid) * 100;

      this.symbols.set(key, symbol);
    });

    // Update position profits
    this.updatePositionProfits();

    // Update account equity
    if (this.accountInfo) {
      this.accountInfo.profit = this.calculateOpenProfit();
      this.accountInfo.equity =
        this.accountInfo.balance + this.accountInfo.profit;
      if (this.accountInfo.margin > 0) {
        this.accountInfo.marginLevel =
          (this.accountInfo.equity / this.accountInfo.margin) * 100;
      }
      this.accountInfo.freeMargin =
        this.accountInfo.equity - this.accountInfo.margin;
    }

    this.notifySubscribers({
      type: "price_update",
      symbols: Array.from(this.symbols.values()),
      account: this.accountInfo,
    });
  }

  private updatePositionProfits(): void {
    this.positions.forEach((position) => {
      const symbol = this.symbols.get(position.symbol);
      if (symbol) {
        position.currentPrice =
          position.type === "BUY" ? symbol.bid : symbol.ask;
        position.profit =
          position.type === "BUY"
            ? (position.currentPrice - position.openPrice) *
              position.volume *
              100
            : (position.openPrice - position.currentPrice) *
              position.volume *
              100;
      }
    });
  }

  private calculateOpenProfit(): number {
    return this.positions.reduce(
      (total, position) => total + position.profit,
      0,
    );
  }
}

// Export singleton instance
export const mt5Service = MT5Service.getInstance();

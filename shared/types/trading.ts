export type Side = "BUY" | "SELL";

export interface Account {
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

export interface Position {
  ticket: number;
  symbol: string;
  type: Side;
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

export interface Trade {
  ticket: number;
  symbol: string;
  type: Side;
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

export interface Signal {
  id: string | number;
  symbol: string;
  direction: Side;
  confidence: number;
  message: string;
  createdAt: string;
}

export interface PerformanceMetrics {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  sharpeRatio: number;
  totalProfit: number;
}

export interface BacktestResultSummary {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  sharpeRatio: number;
  totalProfit: number;
  totalLoss: number;
  netProfit: number;
  averageWin: number;
  averageLoss: number;
  largestWin: number;
  largestLoss: number;
}

export interface BacktestEquityPoint {
  date: string;
  equity: number;
}

export interface BacktestResult {
  id: string;
  status: "running" | "completed" | "failed";
  summary: BacktestResultSummary;
  equityCurve?: BacktestEquityPoint[];
}


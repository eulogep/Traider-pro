import { RequestHandler } from "express";
import { z } from "zod";

// Mock trading data for demonstration
const mockTradingData = {
  performance: {
    totalTrades: 247,
    winRate: 78.4,
    profitFactor: 2.31,
    maxDrawdown: 12.8,
    sharpeRatio: 1.85,
    totalProfit: 15847.32,
    averageWin: 342.5,
    averageLoss: -148.2,
    largestWin: 1250.8,
    largestLoss: -890.4,
    consecutiveWins: 8,
    consecutiveLosses: 3,
  },

  monthlyResults: [
    { month: "2024-01", profit: 2850.5, trades: 28, winRate: 82.1 },
    { month: "2024-02", profit: 1920.3, trades: 24, winRate: 75.0 },
    { month: "2024-03", profit: 3240.8, trades: 31, winRate: 80.6 },
    { month: "2024-04", profit: 2750.2, trades: 29, winRate: 76.9 },
    { month: "2024-05", profit: 3890.4, trades: 35, winRate: 77.1 },
    { month: "2024-06", profit: 1195.12, trades: 22, winRate: 72.7 },
  ],

  dailyPnL: generateDailyPnL(),

  assetAllocation: [
    { symbol: "XAUUSD", percentage: 45, profit: 7200.5 },
    { symbol: "EURUSD", percentage: 25, profit: 3800.2 },
    { symbol: "GBPUSD", percentage: 15, profit: 2100.8 },
    { symbol: "USDJPY", percentage: 10, profit: 1900.32 },
    { symbol: "Others", percentage: 5, profit: 845.5 },
  ],
};

function generateDailyPnL() {
  const data = [];
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 30);

  for (let i = 0; i < 30; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);

    data.push({
      date: date.toISOString().split("T")[0],
      pnl: (Math.random() - 0.4) * 500, // Slightly positive bias
      volume: Math.random() * 10 + 1,
      trades: Math.floor(Math.random() * 8) + 1,
    });
  }

  return data;
}

// Get trading performance overview
export const getPerformanceOverview: RequestHandler = async (req, res) => {
  try {
    res.json({
      success: true,
      data: mockTradingData.performance,
    });
  } catch (error) {
    console.error("Error fetching performance overview:", error);
    res.status(500).json({ error: "Failed to fetch performance data" });
  }
};

// Get monthly performance data
export const getMonthlyPerformance: RequestHandler = async (req, res) => {
  try {
    const { months = 6 } = req.query;
    const numMonths = Math.min(parseInt(months as string) || 6, 12);

    res.json({
      success: true,
      data: mockTradingData.monthlyResults.slice(-numMonths),
    });
  } catch (error) {
    console.error("Error fetching monthly performance:", error);
    res.status(500).json({ error: "Failed to fetch monthly performance data" });
  }
};

// Get daily P&L data
export const getDailyPnL: RequestHandler = async (req, res) => {
  try {
    const { days = 30 } = req.query;
    const numDays = Math.min(parseInt(days as string) || 30, 365);

    res.json({
      success: true,
      data: mockTradingData.dailyPnL.slice(-numDays),
    });
  } catch (error) {
    console.error("Error fetching daily P&L:", error);
    res.status(500).json({ error: "Failed to fetch daily P&L data" });
  }
};

// Get asset allocation
export const getAssetAllocation: RequestHandler = async (req, res) => {
  try {
    res.json({
      success: true,
      data: mockTradingData.assetAllocation,
    });
  } catch (error) {
    console.error("Error fetching asset allocation:", error);
    res.status(500).json({ error: "Failed to fetch asset allocation data" });
  }
};

// Get trading statistics
export const getTradingStats: RequestHandler = async (req, res) => {
  try {
    const { period = "30d" } = req.query;

    // Mock calculation based on period
    let multiplier = 1;
    switch (period) {
      case "7d":
        multiplier = 0.25;
        break;
      case "30d":
        multiplier = 1;
        break;
      case "90d":
        multiplier = 3;
        break;
      case "365d":
        multiplier = 12;
        break;
    }

    const stats = {
      totalTrades: Math.floor(
        mockTradingData.performance.totalTrades * multiplier,
      ),
      totalProfit: mockTradingData.performance.totalProfit * multiplier,
      winRate: mockTradingData.performance.winRate + (Math.random() - 0.5) * 2,
      profitFactor:
        mockTradingData.performance.profitFactor + (Math.random() - 0.5) * 0.2,
      maxDrawdown:
        mockTradingData.performance.maxDrawdown + (Math.random() - 0.5) * 2,
      sharpeRatio:
        mockTradingData.performance.sharpeRatio + (Math.random() - 0.5) * 0.3,
      period,
    };

    res.json({
      success: true,
      data: stats,
    });
  } catch (error) {
    console.error("Error fetching trading stats:", error);
    res.status(500).json({ error: "Failed to fetch trading statistics" });
  }
};

// Get AI insights and recommendations
export const getAIInsights: RequestHandler = async (req, res) => {
  try {
    const insights = [
      {
        id: 1,
        type: "optimization",
        title: "RSI Period Optimization",
        message:
          "Adjusting RSI period from 14 to 17 could improve win rate by 3.2%",
        confidence: 89,
        impact: "medium",
        symbol: "XAUUSD",
        timestamp: new Date().toISOString(),
      },
      {
        id: 2,
        type: "risk",
        title: "Position Size Warning",
        message:
          "Current position size on EURUSD exceeds optimal risk parameters",
        confidence: 94,
        impact: "high",
        symbol: "EURUSD",
        timestamp: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
      },
      {
        id: 3,
        type: "opportunity",
        title: "Market Pattern Detected",
        message: "Strong pullback pattern identified on GBPUSD at 1.2650 level",
        confidence: 87,
        impact: "high",
        symbol: "GBPUSD",
        timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      },
    ];

    res.json({
      success: true,
      data: insights,
    });
  } catch (error) {
    console.error("Error fetching AI insights:", error);
    res.status(500).json({ error: "Failed to fetch AI insights" });
  }
};

// Get risk metrics
export const getRiskMetrics: RequestHandler = async (req, res) => {
  try {
    const riskMetrics = {
      currentRisk: {
        totalExposure: 15250.0,
        riskPerTrade: 2.1,
        maxRiskPercentage: 8.5,
        marginUtilization: 35.2,
        correlationRisk: "Low",
      },
      var: {
        daily: 485.2,
        weekly: 1250.8,
        monthly: 2890.5,
      },
      drawdown: {
        current: 2.3,
        maximum: 12.8,
        recovery: 85.6,
      },
      diversification: {
        score: 78,
        concentration: "Moderate",
        topAssetWeight: 45,
      },
    };

    res.json({
      success: true,
      data: riskMetrics,
    });
  } catch (error) {
    console.error("Error fetching risk metrics:", error);
    res.status(500).json({ error: "Failed to fetch risk metrics" });
  }
};

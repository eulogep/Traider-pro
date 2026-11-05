import "dotenv/config";
import express from "express";
import cors from "cors";
import { handleDemo } from "./routes/demo";
import * as tradingController from "./controllers/tradingController";
import * as optimizationController from "./controllers/optimizationController";
import * as backtestController from "./controllers/backtestController";
import * as settingsController from "./controllers/settingsController";
import { validateBody } from "./middleware/validate";
import { localMutationGuard } from "./middleware/localMutationGuard";
import {
  OptimizationRequestSchema,
  BacktestRequestSchema,
} from "./routes/optimization";
import { env } from "./config/env";

export function createServer() {
  const app = express();

  // Middleware
  // Local research tool: only same-machine origins may call the API.
  app.use(
    cors({
      origin: [/^https?:\/\/localhost(:\d+)?$/, /^https?:\/\/127\.0\.0\.1(:\d+)?$/],
    }),
  );
  // Loopback Host on every /api request; loopback Origin + X-ATO-Request on every mutation (audit N10).
  app.use(localMutationGuard);
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Example API routes
  app.get("/api/ping", (_req, res) => {
    const ping = env.PING_MESSAGE ?? "ping";
    res.json({ message: ping });
  });

  app.get("/api/demo", handleDemo);

  // Trading analytics
  app.get("/api/analytics/performance", tradingController.getPerformanceOverview);
  app.get(
    "/api/analytics/monthly",
    tradingController.getMonthlyPerformance,
  );
  app.get("/api/analytics/daily-pnl", tradingController.getDailyPnL);
  app.get(
    "/api/analytics/asset-allocation",
    tradingController.getAssetAllocation,
  );
  app.get("/api/analytics/stats", tradingController.getTradingStats);
  app.get("/api/analytics/ai-insights", tradingController.getAIInsights);
  app.get("/api/analytics/risk-metrics", tradingController.getRiskMetrics);

  // Settings
  app.get("/api/settings", settingsController.getSettings);
  app.post("/api/settings", settingsController.saveSettings);
  app.post("/api/settings/reset", settingsController.resetSettings);
  app.get("/api/settings/backup", settingsController.backupSettings);

  // Optimization
  app.post(
    "/api/optimize",
    validateBody(OptimizationRequestSchema),
    optimizationController.startOptimization,
  );
  app.get(
    "/api/optimize/status/:id",
    optimizationController.getOptimizationStatus,
  );
  app.get(
    "/api/optimize/results/:id",
    optimizationController.getOptimizationResults,
  );
  app.get(
    "/api/optimize/strategies",
    optimizationController.getAvailableStrategies,
  );
  app.get(
    "/api/optimize/history",
    optimizationController.getOptimizationHistory,
  );

  // Backtests
  app.post(
    "/api/backtest",
    validateBody(BacktestRequestSchema),
    backtestController.startBacktest,
  );
  app.get("/api/backtest/:id", backtestController.getBacktestResults);

  return app;
}

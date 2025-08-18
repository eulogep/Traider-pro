import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Target,
  Play,
  Download,
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Calendar,
  Settings,
  Brain,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle,
  FileText,
} from "lucide-react";

export default function Backtest() {
  const [isRunning, setIsRunning] = useState(false);
  const [timeframe, setTimeframe] = useState("1h");
  const [riskPercent, setRiskPercent] = useState([2]);
  const [useAI, setUseAI] = useState(true);

  const backtestResults = {
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
  };

  const monthlyResults = [
    { month: "Jan 2024", profit: 2850.5, trades: 28, winRate: 82.1 },
    { month: "Feb 2024", profit: 1920.3, trades: 24, winRate: 75.0 },
    { month: "Mar 2024", profit: 3240.8, trades: 31, winRate: 80.6 },
    { month: "Apr 2024", profit: 2750.2, trades: 29, winRate: 76.9 },
    { month: "May 2024", profit: 3890.4, trades: 35, winRate: 77.1 },
    { month: "Jun 2024", profit: 1195.12, trades: 22, winRate: 72.7 },
  ];

  const strategies = [
    { name: "RSI + MACD Crossover", status: "active", lastRun: "2h ago" },
    {
      name: "Support/Resistance Breakout",
      status: "optimizing",
      lastRun: "1d ago",
    },
    {
      name: "Pullback Pattern Recognition",
      status: "completed",
      lastRun: "3h ago",
    },
    { name: "AI Enhanced Momentum", status: "active", lastRun: "30m ago" },
  ];

  const runBacktest = () => {
    setIsRunning(true);
    setTimeout(() => setIsRunning(false), 3000);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Target className="w-8 h-8 mr-3 text-primary" />
              Strategy Backtesting
            </h1>
            <p className="text-muted-foreground">
              Historical performance analysis and strategy validation
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-primary border-primary/20">
              <Brain className="w-4 h-4 mr-2" />
              AI Enhanced
            </Badge>
            <Button
              onClick={runBacktest}
              disabled={isRunning}
              className="bg-primary hover:bg-primary/90"
            >
              {isRunning ? (
                <>
                  <Activity className="w-4 h-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Backtest
                </>
              )}
            </Button>
          </div>
        </div>

        <Tabs defaultValue="parameters" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="parameters">Parameters</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="strategies">Strategies</TabsTrigger>
          </TabsList>

          {/* Parameters Tab */}
          <TabsContent value="parameters" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Settings className="w-5 h-5 mr-2" />
                    Backtest Configuration
                  </CardTitle>
                  <CardDescription>
                    Configure your backtesting parameters
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="start-date">Start Date</Label>
                      <Input
                        id="start-date"
                        type="date"
                        defaultValue="2024-01-01"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="end-date">End Date</Label>
                      <Input
                        id="end-date"
                        type="date"
                        defaultValue="2024-06-30"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="asset">Trading Asset</Label>
                    <Select defaultValue="xauusd">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="xauusd">XAU/USD (Gold)</SelectItem>
                        <SelectItem value="eurusd">EUR/USD</SelectItem>
                        <SelectItem value="gbpusd">GBP/USD</SelectItem>
                        <SelectItem value="usdjpy">USD/JPY</SelectItem>
                        <SelectItem value="btcusd">BTC/USD</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="timeframe">Timeframe</Label>
                    <Select value={timeframe} onValueChange={setTimeframe}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1m">1 Minute</SelectItem>
                        <SelectItem value="5m">5 Minutes</SelectItem>
                        <SelectItem value="15m">15 Minutes</SelectItem>
                        <SelectItem value="1h">1 Hour</SelectItem>
                        <SelectItem value="4h">4 Hours</SelectItem>
                        <SelectItem value="1d">1 Day</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Risk per Trade: {riskPercent[0]}%</Label>
                    <Slider
                      value={riskPercent}
                      onValueChange={setRiskPercent}
                      max={10}
                      min={0.1}
                      step={0.1}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="initial-balance">Initial Balance</Label>
                    <Input
                      id="initial-balance"
                      type="number"
                      defaultValue="10000"
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Brain className="w-5 h-5 mr-2" />
                    AI Optimization
                  </CardTitle>
                  <CardDescription>
                    Configure AI enhancement features
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>AI Strategy Enhancement</Label>
                      <p className="text-sm text-muted-foreground">
                        Use AI to optimize entry/exit points
                      </p>
                    </div>
                    <Switch checked={useAI} onCheckedChange={setUseAI} />
                  </div>

                  <div className="space-y-2">
                    <Label>Optimization Algorithm</Label>
                    <Select defaultValue="xgboost">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="xgboost">XGBoost</SelectItem>
                        <SelectItem value="random-forest">
                          Random Forest
                        </SelectItem>
                        <SelectItem value="lstm">
                          LSTM Neural Network
                        </SelectItem>
                        <SelectItem value="genetic">
                          Genetic Algorithm
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Technical Indicators</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        "RSI",
                        "MACD",
                        "Support/Resistance",
                        "Bollinger Bands",
                        "Moving Averages",
                        "Stochastic",
                      ].map((indicator) => (
                        <div
                          key={indicator}
                          className="flex items-center space-x-2"
                        >
                          <input
                            type="checkbox"
                            defaultChecked
                            className="rounded"
                          />
                          <Label className="text-sm">{indicator}</Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Pattern Recognition</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {["Pullback", "Breakout", "Reversal", "Continuation"].map(
                        (pattern) => (
                          <div
                            key={pattern}
                            className="flex items-center space-x-2"
                          >
                            <input
                              type="checkbox"
                              defaultChecked
                              className="rounded"
                            />
                            <Label className="text-sm">{pattern}</Label>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results" className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Total Profit
                      </p>
                      <p className="text-xl font-bold text-trading-green-500">
                        ${backtestResults.totalProfit.toLocaleString()}
                      </p>
                    </div>
                    <DollarSign className="w-6 h-6 text-trading-green-500" />
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Win Rate</p>
                      <p className="text-xl font-bold text-primary">
                        {backtestResults.winRate}%
                      </p>
                    </div>
                    <Target className="w-6 h-6 text-primary" />
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Profit Factor
                      </p>
                      <p className="text-xl font-bold text-accent">
                        {backtestResults.profitFactor}
                      </p>
                    </div>
                    <BarChart3 className="w-6 h-6 text-accent" />
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Max Drawdown
                      </p>
                      <p className="text-xl font-bold text-trading-red-500">
                        {backtestResults.maxDrawdown}%
                      </p>
                    </div>
                    <TrendingDown className="w-6 h-6 text-trading-red-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Monthly Performance</CardTitle>
                <CardDescription>
                  Breakdown of monthly trading results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {monthlyResults.map((month, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg border border-border/30"
                    >
                      <div className="flex items-center space-x-4">
                        <Calendar className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium">{month.month}</span>
                        <Badge variant="secondary">{month.trades} trades</Badge>
                      </div>
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-muted-foreground">
                          {month.winRate}% win rate
                        </span>
                        <span
                          className={`font-medium ${month.profit > 0 ? "text-trading-green-500" : "text-trading-red-500"}`}
                        >
                          ${month.profit.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analysis Tab */}
          <TabsContent value="analysis" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Trade Statistics</CardTitle>
                  <CardDescription>
                    Detailed analysis of trading performance
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Total Trades
                      </p>
                      <p className="text-lg font-semibold">
                        {backtestResults.totalTrades}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Sharpe Ratio
                      </p>
                      <p className="text-lg font-semibold">
                        {backtestResults.sharpeRatio}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Average Win
                      </p>
                      <p className="text-lg font-semibold text-trading-green-500">
                        ${backtestResults.averageWin}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Average Loss
                      </p>
                      <p className="text-lg font-semibold text-trading-red-500">
                        ${backtestResults.averageLoss}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Largest Win
                      </p>
                      <p className="text-lg font-semibold text-trading-green-500">
                        ${backtestResults.largestWin}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Largest Loss
                      </p>
                      <p className="text-lg font-semibold text-trading-red-500">
                        ${backtestResults.largestLoss}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Risk Analysis</CardTitle>
                  <CardDescription>
                    Risk metrics and recommendations
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-trading-green-500/10 border border-trading-green-500/20">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-trading-green-500" />
                        <span className="text-sm">
                          Excellent win rate consistency
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-accent/10 border border-accent/20">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 text-accent" />
                        <span className="text-sm">
                          Monitor consecutive losses
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
                      <div className="flex items-center space-x-2">
                        <Brain className="w-4 h-4 text-primary" />
                        <span className="text-sm">
                          AI recommends position size optimization
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Strategies Tab */}
          <TabsContent value="strategies" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Strategy Performance</CardTitle>
                <CardDescription>
                  Compare different trading strategies
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {strategies.map((strategy, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-4 rounded-lg border border-border/30"
                    >
                      <div className="flex items-center space-x-4">
                        <div
                          className={`w-3 h-3 rounded-full ${
                            strategy.status === "active"
                              ? "bg-trading-green-500"
                              : strategy.status === "optimizing"
                                ? "bg-accent animate-pulse"
                                : "bg-muted-foreground"
                          }`}
                        />
                        <div>
                          <h4 className="font-medium">{strategy.name}</h4>
                          <p className="text-sm text-muted-foreground">
                            Last run: {strategy.lastRun}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Badge
                          variant={
                            strategy.status === "active"
                              ? "default"
                              : strategy.status === "optimizing"
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {strategy.status}
                        </Badge>
                        <Button variant="outline" size="sm">
                          <FileText className="w-4 h-4 mr-2" />
                          View Report
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export Results
          </Button>
          <Button variant="outline">
            <FileText className="w-4 h-4 mr-2" />
            Generate Report
          </Button>
        </div>
      </div>
    </div>
  );
}

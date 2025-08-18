import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TradingChart,
  PerformanceMetrics,
  MarketOverview,
} from "@/components/TradingChart";
import { MT5AccountSummary } from "@/components/MT5Connection";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Activity,
  Target,
  Zap,
  RefreshCw,
  Settings,
  Brain,
  AlertTriangle,
  CheckCircle,
  Clock,
  Eye,
  Bell,
} from "lucide-react";

export default function Dashboard() {
  const recentTrades = [
    {
      pair: "XAU/USD",
      action: "BUY",
      profit: "+$234.50",
      time: "2h ago",
      status: "closed",
    },
    {
      pair: "EUR/USD",
      action: "SELL",
      profit: "+$156.20",
      time: "4h ago",
      status: "closed",
    },
    {
      pair: "GBP/USD",
      action: "BUY",
      profit: "-$89.30",
      time: "6h ago",
      status: "closed",
    },
    {
      pair: "XAU/USD",
      action: "SELL",
      profit: "+$412.80",
      time: "8h ago",
      status: "closed",
    },
    {
      pair: "USD/JPY",
      action: "BUY",
      profit: "Running",
      time: "1h ago",
      status: "open",
    },
  ];

  const aiInsights = [
    {
      title: "Pattern Recognition Alert",
      message: "XAU/USD showing strong pullback pattern at 1,985 level",
      type: "opportunity",
      confidence: "92%",
    },
    {
      title: "Risk Management Warning",
      message: "Current EUR/USD position approaching stop-loss threshold",
      type: "warning",
      confidence: "87%",
    },
    {
      title: "Optimization Suggestion",
      message: "RSI period adjustment could improve win rate by 3.2%",
      type: "optimization",
      confidence: "78%",
    },
  ];

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold">Trading Dashboard</h1>
            <p className="text-muted-foreground">
              Real-time performance and AI insights
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="text-trading-green-500 border-trading-green-500"
            >
              <div className="w-2 h-2 bg-trading-green-500 rounded-full mr-2 animate-pulse" />
              Live Trading
            </Badge>
            <Button variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        {/* Performance Metrics */}
        <PerformanceMetrics />

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Interactive Trading Chart */}
          <div className="lg:col-span-2">
            <TradingChart
              title="Portfolio Performance"
              type="area"
              timeframe="6M"
            />
          </div>

          {/* AI Insights */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Brain className="w-5 h-5 mr-2" />
                AI Insights
              </CardTitle>
              <CardDescription>
                Real-time optimization suggestions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {aiInsights.map((insight, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg border border-border/50 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">{insight.title}</h4>
                    <Badge
                      variant={
                        insight.type === "warning"
                          ? "destructive"
                          : insight.type === "opportunity"
                            ? "default"
                            : "secondary"
                      }
                      className="text-xs"
                    >
                      {insight.confidence}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {insight.message}
                  </p>
                  <div className="flex items-center justify-between pt-2">
                    <Button variant="outline" size="sm">
                      <Eye className="w-3 h-3 mr-1" />
                      Details
                    </Button>
                    <Button variant="default" size="sm">
                      Apply
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Secondary Charts */}
        <div className="grid lg:grid-cols-2 gap-6">
          <TradingChart title="Hourly P&L" type="bar" timeframe="1D" />
          <TradingChart
            title="Asset Allocation"
            type="pie"
            timeframe="Current"
          />
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Recent Trades */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="w-5 h-5 mr-2" />
                Recent Trades
              </CardTitle>
              <CardDescription>
                Latest trading activity and results
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentTrades.map((trade, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-lg border border-border/30 hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center space-x-4">
                      <Badge
                        variant={
                          trade.action === "BUY" ? "default" : "secondary"
                        }
                      >
                        {trade.action}
                      </Badge>
                      <span className="font-medium">{trade.pair}</span>
                      <span className="text-sm text-muted-foreground flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {trade.time}
                      </span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Badge
                        variant={
                          trade.status === "open" ? "outline" : "secondary"
                        }
                        className={
                          trade.status === "open"
                            ? "border-accent text-accent animate-pulse"
                            : ""
                        }
                      >
                        {trade.status}
                      </Badge>
                      <span
                        className={`font-medium ${
                          trade.profit.includes("+")
                            ? "text-trading-green-500"
                            : trade.profit.includes("-")
                              ? "text-trading-red-500"
                              : "text-muted-foreground"
                        }`}
                      >
                        {trade.profit}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Market Overview */}
          <MarketOverview />
        </div>

        {/* System Status */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="w-5 h-5 mr-2" />
              System Status
            </CardTitle>
            <CardDescription>
              Real-time system health monitoring
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30">
                <CheckCircle className="w-5 h-5 text-trading-green-500" />
                <div>
                  <p className="font-medium">MT5 Connection</p>
                  <p className="text-xs text-muted-foreground">Connected</p>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30">
                <CheckCircle className="w-5 h-5 text-trading-green-500" />
                <div>
                  <p className="font-medium">AI Engine</p>
                  <p className="text-xs text-muted-foreground">Running</p>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30">
                <AlertTriangle className="w-5 h-5 text-accent" />
                <div>
                  <p className="font-medium">Data Feed</p>
                  <p className="text-xs text-muted-foreground">Delayed 2s</p>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30">
                <CheckCircle className="w-5 h-5 text-trading-green-500" />
                <div>
                  <p className="font-medium">Risk Manager</p>
                  <p className="text-xs text-muted-foreground">Active</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

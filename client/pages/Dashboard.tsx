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
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Activity,
  Target,
  Zap,
  RefreshCw,
  Settings,
} from "lucide-react";

export default function Dashboard() {
  const performanceMetrics = [
    {
      label: "Total Profit",
      value: "$12,847.32",
      change: "+18.4%",
      trend: "up",
      icon: DollarSign,
      color: "text-trading-green-500",
    },
    {
      label: "Win Rate",
      value: "78.4%",
      change: "+2.1%",
      trend: "up",
      icon: Target,
      color: "text-primary",
    },
    {
      label: "Max Drawdown",
      value: "12.8%",
      change: "-3.2%",
      trend: "down",
      icon: TrendingDown,
      color: "text-trading-red-500",
    },
    {
      label: "Profit Factor",
      value: "2.31",
      change: "+0.15",
      trend: "up",
      icon: BarChart3,
      color: "text-accent",
    },
  ];

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {performanceMetrics.map((metric, index) => {
            const Icon = metric.icon;
            return (
              <Card key={index} className="border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        {metric.label}
                      </p>
                      <p className="text-2xl font-bold">{metric.value}</p>
                      <p
                        className={`text-sm flex items-center ${
                          metric.trend === "up"
                            ? "text-trading-green-500"
                            : "text-trading-red-500"
                        }`}
                      >
                        {metric.trend === "up" ? (
                          <TrendingUp className="w-4 h-4 mr-1" />
                        ) : (
                          <TrendingDown className="w-4 h-4 mr-1" />
                        )}
                        {metric.change}
                      </p>
                    </div>
                    <Icon className={`w-8 h-8 ${metric.color}`} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Trading Chart Placeholder */}
          <Card className="lg:col-span-2 border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <BarChart3 className="w-5 h-5 mr-2" />
                Portfolio Performance
              </CardTitle>
              <CardDescription>
                Last 30 days performance overview
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-gradient-to-br from-primary/5 to-accent/5 rounded-lg flex items-center justify-center border border-border/30">
                <div className="text-center">
                  <Activity className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">
                    Interactive chart will be displayed here
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Connect MT5 for live data visualization
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI Insights */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Zap className="w-5 h-5 mr-2" />
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
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

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
                  className="flex items-center justify-between p-3 rounded-lg border border-border/30"
                >
                  <div className="flex items-center space-x-4">
                    <Badge
                      variant={trade.action === "BUY" ? "default" : "secondary"}
                    >
                      {trade.action}
                    </Badge>
                    <span className="font-medium">{trade.pair}</span>
                    <span className="text-sm text-muted-foreground">
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
                          ? "border-accent text-accent"
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
      </div>
    </div>
  );
}

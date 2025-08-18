import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useMT5, useMT5Account } from "@/hooks/useMT5";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  DollarSign,
  Target,
  Maximize2,
  Settings,
} from "lucide-react";

interface TradingChartProps {
  title?: string;
  type?: "line" | "area" | "bar" | "pie";
  timeframe?: string;
  className?: string;
}

// Sample data - in real app this would come from props or API
const performanceData = [
  { date: "Jan", profit: 2850, trades: 28, winRate: 82 },
  { date: "Feb", profit: 1920, trades: 24, winRate: 75 },
  { date: "Mar", profit: 3240, trades: 31, winRate: 81 },
  { date: "Apr", profit: 2750, trades: 29, winRate: 77 },
  { date: "May", profit: 3890, trades: 35, winRate: 79 },
  { date: "Jun", profit: 1195, trades: 22, winRate: 73 },
];

const equityCurveData = [
  { time: "00:00", equity: 10000, drawdown: 0 },
  { time: "04:00", equity: 10250, drawdown: -2.1 },
  { time: "08:00", equity: 10180, drawdown: -0.7 },
  { time: "12:00", equity: 10520, drawdown: 0 },
  { time: "16:00", equity: 10890, drawdown: 0 },
  { time: "20:00", equity: 11240, drawdown: 0 },
];

const assetAllocation = [
  { name: "XAU/USD", value: 45, color: "#22c55e" },
  { name: "EUR/USD", value: 25, color: "#3b82f6" },
  { name: "GBP/USD", value: 15, color: "#f59e0b" },
  { name: "USD/JPY", value: 10, color: "#ef4444" },
  { name: "Others", value: 5, color: "#8b5cf6" },
];

const hourlyPnL = [
  { hour: "00", pnl: 45 },
  { hour: "01", pnl: -12 },
  { hour: "02", pnl: 23 },
  { hour: "03", pnl: 67 },
  { hour: "04", pnl: -34 },
  { hour: "05", pnl: 89 },
  { hour: "06", pnl: 156 },
  { hour: "07", pnl: -78 },
  { hour: "08", pnl: 234 },
  { hour: "09", pnl: 123 },
  { hour: "10", pnl: -45 },
  { hour: "11", pnl: 67 },
];

export function TradingChart({ title = "Trading Performance", type = "line", timeframe = "6M" }: TradingChartProps) {
  const [chartType, setChartType] = useState(type);
  const [selectedTimeframe, setSelectedTimeframe] = useState(timeframe);
  const { summary } = useMT5Account();

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="font-medium">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {`${entry.dataKey}: ${entry.value}${entry.dataKey === 'profit' ? '$' : entry.dataKey === 'winRate' ? '%' : ''}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    switch (chartType) {
      case "area":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={performanceData}>
              <defs>
                <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(210, 20%, 15%)" />
              <XAxis dataKey="date" stroke="hsl(215, 20%, 65%)" />
              <YAxis stroke="hsl(215, 20%, 65%)" />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="profit" 
                stroke="hsl(142, 76%, 36%)" 
                fill="url(#profitGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        );
      
      case "bar":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={hourlyPnL}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(210, 20%, 15%)" />
              <XAxis dataKey="hour" stroke="hsl(215, 20%, 65%)" />
              <YAxis stroke="hsl(215, 20%, 65%)" />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey="pnl" 
                fill={(entry: any) => entry.pnl >= 0 ? "hsl(142, 76%, 36%)" : "hsl(0, 84%, 60%)"}
              />
            </BarChart>
          </ResponsiveContainer>
        );
      
      case "pie":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={assetAllocation}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {assetAllocation.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );
      
      default: // line
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityCurveData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(210, 20%, 15%)" />
              <XAxis dataKey="time" stroke="hsl(215, 20%, 65%)" />
              <YAxis stroke="hsl(215, 20%, 65%)" />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="equity" 
                stroke="hsl(142, 76%, 36%)" 
                strokeWidth={2}
                dot={{ fill: "hsl(142, 76%, 36%)", r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey="drawdown" 
                stroke="hsl(0, 84%, 60%)" 
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: "hsl(0, 84%, 60%)", r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <Card className="border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center">
              <BarChart3 className="w-5 h-5 mr-2" />
              {title}
            </CardTitle>
            <CardDescription>
              {chartType === 'pie' ? 'Asset allocation breakdown' : `Performance over ${selectedTimeframe}`}
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Select value={chartType} onValueChange={setChartType}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="line">Line</SelectItem>
                <SelectItem value="area">Area</SelectItem>
                <SelectItem value="bar">Bar</SelectItem>
                <SelectItem value="pie">Pie</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
              <SelectTrigger className="w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1D">1D</SelectItem>
                <SelectItem value="1W">1W</SelectItem>
                <SelectItem value="1M">1M</SelectItem>
                <SelectItem value="3M">3M</SelectItem>
                <SelectItem value="6M">6M</SelectItem>
                <SelectItem value="1Y">1Y</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm">
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {renderChart()}
        
        {/* Chart Stats - Use real MT5 data when available */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Balance</p>
            <p className="text-lg font-bold text-trading-green-500">${summary.balance.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Equity</p>
            <p className="text-lg font-bold text-primary">${summary.equity.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Open P&L</p>
            <p className={`text-lg font-bold ${summary.profit >= 0 ? 'text-trading-green-500' : 'text-trading-red-500'}`}>
              {summary.profit >= 0 ? '+' : ''}${summary.profit.toFixed(2)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Positions</p>
            <p className="text-lg font-bold text-accent">{summary.openPositions}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Performance metrics component - now using real MT5 data
export function PerformanceMetrics() {
  const { summary, connected } = useMT5Account();

  const metrics = [
    {
      label: "Account Balance",
      value: `$${summary.balance.toLocaleString()}`,
      change: connected ? "+2.4%" : "N/A",
      trend: "up",
      icon: DollarSign,
      color: "text-trading-green-500"
    },
    {
      label: "Current Equity",
      value: `$${summary.equity.toLocaleString()}`,
      change: connected ? `${summary.profit >= 0 ? '+' : ''}$${summary.profit.toFixed(2)}` : "N/A",
      trend: summary.profit >= 0 ? "up" : "down",
      icon: Target,
      color: "text-primary"
    },
    {
      label: "Open Positions",
      value: summary.openPositions.toString(),
      change: connected ? "Active" : "N/A",
      trend: "up",
      icon: Activity,
      color: "text-accent"
    },
    {
      label: "Free Margin",
      value: `$${summary.freeMargin.toLocaleString()}`,
      change: connected ? `${summary.marginLevel.toFixed(1)}%` : "N/A",
      trend: "up",
      icon: TrendingUp,
      color: "text-trading-green-500"
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, index) => {
        const Icon = metric.icon;
        return (
          <Card key={index} className="border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{metric.label}</p>
                  <p className="text-xl font-bold">{metric.value}</p>
                  <p className={`text-sm flex items-center ${
                    metric.trend === 'up' ? 'text-trading-green-500' : 'text-trading-red-500'
                  }`}>
                    {metric.trend === 'up' ? 
                      <TrendingUp className="w-3 h-3 mr-1" /> : 
                      <TrendingDown className="w-3 h-3 mr-1" />
                    }
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
  );
}

// Real-time market data component - now using real MT5 data
export function MarketOverview() {
  const { symbols, connected } = useMT5();
  const displaySymbols = symbols.length > 0 ? symbols.slice(0, 5) : [
    { symbol: "XAU/USD", price: "1,985.45", change: "+12.80", changePercent: "+0.65%", trend: "up" },
    { symbol: "EUR/USD", price: "1.0875", change: "-0.0023", changePercent: "-0.21%", trend: "down" },
    { symbol: "GBP/USD", price: "1.2634", change: "+0.0045", changePercent: "+0.36%", trend: "up" },
    { symbol: "USD/JPY", price: "149.82", change: "-0.34", changePercent: "-0.23%", trend: "down" },
    { symbol: "BTC/USD", price: "42,567", change: "+1,234", changePercent: "+2.98%", trend: "up" },
  ];

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Market Overview
          {connected && (
            <Badge variant="outline" className="ml-2 text-trading-green-500 border-trading-green-500">
              Live
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          {connected ? "Real-time MT5 market prices" : "Sample market data (connect MT5 for live prices)"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {connected ? (
            symbols.slice(0, 5).map((symbol, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-border/30">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    symbol.change >= 0 ? 'bg-trading-green-500' : 'bg-trading-red-500'
                  } animate-pulse`} />
                  <span className="font-medium">{symbol.symbol}</span>
                </div>
                <div className="text-right">
                  <p className="font-medium">{symbol.bid.toFixed(symbol.digits)}</p>
                  <p className={`text-sm ${
                    symbol.change >= 0 ? 'text-trading-green-500' : 'text-trading-red-500'
                  }`}>
                    {symbol.change >= 0 ? '+' : ''}{symbol.changePercent.toFixed(2)}%
                  </p>
                </div>
              </div>
            ))
          ) : (
            displaySymbols.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-border/30 opacity-60">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    (item as any).trend === 'up' ? 'bg-trading-green-500' : 'bg-trading-red-500'
                  }`} />
                  <span className="font-medium">{(item as any).symbol}</span>
                </div>
                <div className="text-right">
                  <p className="font-medium">{(item as any).price}</p>
                  <p className={`text-sm ${
                    (item as any).trend === 'up' ? 'text-trading-green-500' : 'text-trading-red-500'
                  }`}>
                    {(item as any).change} ({(item as any).changePercent})
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

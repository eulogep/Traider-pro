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
import { Progress } from "@/components/ui/progress";
import {
  Brain,
  Zap,
  Target,
  Settings,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  Play,
  Pause,
  RefreshCw,
  Download,
  Upload,
  AlertTriangle,
  CheckCircle,
  Lightbulb,
  Cpu,
  Database,
  Eye,
} from "lucide-react";

export default function Optimizer() {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationProgress, setOptimizationProgress] = useState(0);
  const [selectedModel, setSelectedModel] = useState("xgboost");
  const [aggressiveness, setAggressiveness] = useState([50]);

  const optimizationResults = [
    {
      strategy: "RSI + MACD Enhanced",
      improvement: "+23.4%",
      winRate: "82.1%",
      profitFactor: "2.67",
      status: "optimized",
      confidence: 94,
    },
    {
      strategy: "Support/Resistance AI",
      improvement: "+18.7%",
      winRate: "76.8%",
      profitFactor: "2.31",
      status: "optimizing",
      confidence: 87,
    },
    {
      strategy: "Pullback Pattern Recognition",
      improvement: "+15.2%",
      winRate: "79.3%",
      profitFactor: "2.45",
      status: "pending",
      confidence: 91,
    },
  ];

  const aiInsights = [
    {
      type: "optimization",
      title: "RSI Period Adjustment",
      description:
        "Changing RSI period from 14 to 17 could improve win rate by 4.2%",
      impact: "High",
      confidence: 89,
    },
    {
      type: "risk",
      title: "Stop Loss Optimization",
      description:
        "Dynamic stop loss based on volatility could reduce max drawdown by 23%",
      impact: "Medium",
      confidence: 76,
    },
    {
      type: "entry",
      title: "Entry Point Refinement",
      description:
        "ML model suggests waiting for additional confirmation signals",
      impact: "High",
      confidence: 92,
    },
  ];

  const startOptimization = () => {
    setIsOptimizing(true);
    setOptimizationProgress(0);

    const interval = setInterval(() => {
      setOptimizationProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsOptimizing(false);
          return 100;
        }
        return prev + Math.random() * 10;
      });
    }, 500);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Brain className="w-8 h-8 mr-3 text-primary" />
              AI Strategy Optimizer
            </h1>
            <p className="text-muted-foreground">
              Automatic strategy optimization using machine learning
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-accent border-accent/20">
              <Cpu className="w-4 h-4 mr-2" />
              XGBoost Model
            </Badge>
            <Button
              onClick={startOptimization}
              disabled={isOptimizing}
              className="bg-primary hover:bg-primary/90"
            >
              {isOptimizing ? (
                <>
                  <Activity className="w-4 h-4 mr-2 animate-spin" />
                  Optimizing...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2" />
                  Start Optimization
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Optimization Progress */}
        {isOptimizing && (
          <Card className="border-border/50">
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold">Optimization in Progress</h3>
                  <span className="text-sm text-muted-foreground">
                    {Math.round(optimizationProgress)}%
                  </span>
                </div>
                <Progress value={optimizationProgress} className="w-full" />
                <p className="text-sm text-muted-foreground">
                  Analyzing {Math.floor(optimizationProgress * 50)} parameter
                  combinations...
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="configure" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="configure">Configure</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="insights">AI Insights</TabsTrigger>
            <TabsTrigger value="models">Models</TabsTrigger>
          </TabsList>

          {/* Configure Tab */}
          <TabsContent value="configure" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Settings className="w-5 h-5 mr-2" />
                    Optimization Parameters
                  </CardTitle>
                  <CardDescription>
                    Configure AI optimization settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label>AI Model</Label>
                    <Select
                      value={selectedModel}
                      onValueChange={setSelectedModel}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="xgboost">
                          XGBoost (Recommended)
                        </SelectItem>
                        <SelectItem value="random-forest">
                          Random Forest
                        </SelectItem>
                        <SelectItem value="lstm">
                          LSTM Neural Network
                        </SelectItem>
                        <SelectItem value="genetic">
                          Genetic Algorithm
                        </SelectItem>
                        <SelectItem value="ensemble">
                          Ensemble Method
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Target Asset</Label>
                    <Select defaultValue="xauusd">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="xauusd">XAU/USD (Gold)</SelectItem>
                        <SelectItem value="eurusd">EUR/USD</SelectItem>
                        <SelectItem value="gbpusd">GBP/USD</SelectItem>
                        <SelectItem value="usdjpy">USD/JPY</SelectItem>
                        <SelectItem value="multiple">
                          Multiple Assets
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Optimization Goal</Label>
                    <Select defaultValue="profit-factor">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="profit-factor">
                          Maximize Profit Factor
                        </SelectItem>
                        <SelectItem value="win-rate">
                          Improve Win Rate
                        </SelectItem>
                        <SelectItem value="sharpe">
                          Optimize Sharpe Ratio
                        </SelectItem>
                        <SelectItem value="drawdown">
                          Minimize Drawdown
                        </SelectItem>
                        <SelectItem value="balanced">
                          Balanced Approach
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>
                      Optimization Aggressiveness: {aggressiveness[0]}%
                    </Label>
                    <Slider
                      value={aggressiveness}
                      onValueChange={setAggressiveness}
                      max={100}
                      min={1}
                      step={1}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Higher values explore more parameter combinations but take
                      longer
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Time Horizon</Label>
                    <Select defaultValue="6m">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1m">1 Month</SelectItem>
                        <SelectItem value="3m">3 Months</SelectItem>
                        <SelectItem value="6m">6 Months</SelectItem>
                        <SelectItem value="1y">1 Year</SelectItem>
                        <SelectItem value="2y">2 Years</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Target className="w-5 h-5 mr-2" />
                    Strategy Components
                  </CardTitle>
                  <CardDescription>
                    Select components to optimize
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="space-y-3">
                      <Label className="text-sm font-medium">
                        Technical Indicators
                      </Label>
                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { name: "RSI", param: "Period: 14" },
                          { name: "MACD", param: "12,26,9" },
                          { name: "Support/Resistance", param: "Lookback: 20" },
                          { name: "Bollinger Bands", param: "Period: 20" },
                          { name: "Moving Averages", param: "SMA 50,200" },
                          { name: "Stochastic", param: "%K: 14" },
                        ].map((indicator, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                defaultChecked
                                className="rounded"
                              />
                              <Label className="text-sm">
                                {indicator.name}
                              </Label>
                            </div>
                            <p className="text-xs text-muted-foreground ml-5">
                              {indicator.param}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <Label className="text-sm font-medium">
                        Risk Management
                      </Label>
                      <div className="space-y-2">
                        {[
                          "Stop Loss Optimization",
                          "Take Profit Levels",
                          "Position Sizing",
                          "Trailing Stops",
                          "Risk/Reward Ratios",
                        ].map((component, index) => (
                          <div
                            key={index}
                            className="flex items-center space-x-2"
                          >
                            <input
                              type="checkbox"
                              defaultChecked
                              className="rounded"
                            />
                            <Label className="text-sm">{component}</Label>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <Label className="text-sm font-medium">
                        Entry/Exit Logic
                      </Label>
                      <div className="space-y-2">
                        {[
                          "Pattern Recognition",
                          "Signal Confirmation",
                          "Market Timing",
                          "Volatility Filters",
                        ].map((logic, index) => (
                          <div
                            key={index}
                            className="flex items-center space-x-2"
                          >
                            <input
                              type="checkbox"
                              defaultChecked
                              className="rounded"
                            />
                            <Label className="text-sm">{logic}</Label>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Optimization Results</CardTitle>
                <CardDescription>
                  AI-enhanced strategy performance improvements
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {optimizationResults.map((result, index) => (
                    <div
                      key={index}
                      className="p-4 rounded-lg border border-border/30 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div
                            className={`w-3 h-3 rounded-full ${
                              result.status === "optimized"
                                ? "bg-trading-green-500"
                                : result.status === "optimizing"
                                  ? "bg-accent animate-pulse"
                                  : "bg-muted-foreground"
                            }`}
                          />
                          <h4 className="font-medium">{result.strategy}</h4>
                          <Badge
                            variant={
                              result.status === "optimized"
                                ? "default"
                                : result.status === "optimizing"
                                  ? "secondary"
                                  : "outline"
                            }
                          >
                            {result.status}
                          </Badge>
                        </div>
                        <div className="flex items-center space-x-4">
                          <span className="text-trading-green-500 font-medium">
                            {result.improvement}
                          </span>
                          <Badge variant="outline">
                            {result.confidence}% confidence
                          </Badge>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">
                            Win Rate:{" "}
                          </span>
                          <span className="font-medium">{result.winRate}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">
                            Profit Factor:{" "}
                          </span>
                          <span className="font-medium">
                            {result.profitFactor}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button variant="outline" size="sm">
                            <Eye className="w-4 h-4 mr-1" />
                            View Details
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Insights Tab */}
          <TabsContent value="insights" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Lightbulb className="w-5 h-5 mr-2" />
                  AI Optimization Insights
                </CardTitle>
                <CardDescription>
                  Machine learning recommendations for strategy improvement
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {aiInsights.map((insight, index) => (
                    <div
                      key={index}
                      className="p-4 rounded-lg border border-border/30 space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center space-x-2">
                            {insight.type === "optimization" && (
                              <TrendingUp className="w-4 h-4 text-primary" />
                            )}
                            {insight.type === "risk" && (
                              <AlertTriangle className="w-4 h-4 text-accent" />
                            )}
                            {insight.type === "entry" && (
                              <Target className="w-4 h-4 text-trading-green-500" />
                            )}
                            <h4 className="font-medium">{insight.title}</h4>
                            <Badge
                              variant={
                                insight.impact === "High"
                                  ? "default"
                                  : insight.impact === "Medium"
                                    ? "secondary"
                                    : "outline"
                              }
                              className="text-xs"
                            >
                              {insight.impact} Impact
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {insight.description}
                          </p>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className="text-sm text-muted-foreground">
                            {insight.confidence}% confidence
                          </span>
                          <Button variant="outline" size="sm">
                            Apply
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Models Tab */}
          <TabsContent value="models" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Available Models</CardTitle>
                  <CardDescription>
                    Choose the best AI model for your strategy
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {[
                    {
                      name: "XGBoost",
                      description: "Gradient boosting for high accuracy",
                      performance: 94,
                      speed: "Fast",
                      recommended: true,
                    },
                    {
                      name: "Random Forest",
                      description: "Ensemble method with good interpretability",
                      performance: 87,
                      speed: "Medium",
                      recommended: false,
                    },
                    {
                      name: "LSTM Neural Network",
                      description: "Deep learning for pattern recognition",
                      performance: 91,
                      speed: "Slow",
                      recommended: false,
                    },
                    {
                      name: "Genetic Algorithm",
                      description: "Evolutionary optimization approach",
                      performance: 85,
                      speed: "Very Slow",
                      recommended: false,
                    },
                  ].map((model, index) => (
                    <div
                      key={index}
                      className="p-3 rounded-lg border border-border/30"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium">{model.name}</h4>
                          {model.recommended && (
                            <Badge variant="default" className="text-xs">
                              Recommended
                            </Badge>
                          )}
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {model.speed}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        {model.description}
                      </p>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs">Performance:</span>
                        <Progress
                          value={model.performance}
                          className="flex-1 h-2"
                        />
                        <span className="text-xs">{model.performance}%</span>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Model Management</CardTitle>
                  <CardDescription>
                    Import/export optimization models
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <Button variant="outline" className="w-full">
                      <Upload className="w-4 h-4 mr-2" />
                      Import Custom Model
                    </Button>
                    <Button variant="outline" className="w-full">
                      <Download className="w-4 h-4 mr-2" />
                      Export Current Model
                    </Button>
                    <Button variant="outline" className="w-full">
                      <Database className="w-4 h-4 mr-2" />
                      Model Library
                    </Button>
                  </div>

                  <div className="mt-6 p-3 rounded-lg bg-primary/10 border border-primary/20">
                    <div className="flex items-start space-x-2">
                      <Lightbulb className="w-4 h-4 text-primary mt-0.5" />
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Pro Tip</p>
                        <p className="text-xs text-muted-foreground">
                          Combine multiple models using ensemble methods for
                          better performance
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          <Button variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Reset Parameters
          </Button>
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export Strategy
          </Button>
        </div>
      </div>
    </div>
  );
}

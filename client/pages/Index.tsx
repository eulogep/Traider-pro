import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  Brain,
  Target,
  Zap,
  BarChart3,
  DollarSign,
  TrendingDown,
  Activity,
  ArrowRight,
  CheckCircle,
  Shield,
  Lightbulb,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function Index() {
  const features = [
    {
      icon: Brain,
      title: "AI Strategy Analysis",
      description:
        "Analyzes your manual Forex/Gold strategies and optimizes them automatically",
      color: "text-primary",
    },
    {
      icon: Target,
      title: "Backtesting Engine",
      description: "Tests performance on historical data with precise accuracy",
      color: "text-accent",
    },
    {
      icon: Zap,
      title: "Semi-Automated Trading",
      description: "Robot trading with manual validation for ultimate control",
      color: "text-trading-gold-500",
    },
    {
      icon: Shield,
      title: "Risk Management",
      description:
        "Advanced money management with multiple TP, trailing stops, and position sizing",
      color: "text-trading-green-500",
    },
    {
      icon: Activity,
      title: "Anomaly Detection",
      description:
        "Identifies weaknesses, abnormal losses, and optimization opportunities",
      color: "text-trading-red-500",
    },
    {
      icon: BarChart3,
      title: "Live Analytics",
      description: "Real-time performance monitoring with MT5 integration",
      color: "text-chart-line-blue",
    },
  ];

  const stats = [
    {
      label: "Win Rate",
      value: "78.4%",
      icon: TrendingUp,
      color: "text-trading-green-500",
    },
    {
      label: "Profit Factor",
      value: "2.31",
      icon: DollarSign,
      color: "text-trading-gold-500",
    },
    {
      label: "Max Drawdown",
      value: "12.8%",
      icon: TrendingDown,
      color: "text-trading-red-500",
    },
    {
      label: "Sharpe Ratio",
      value: "1.85",
      icon: BarChart3,
      color: "text-chart-line-blue",
    },
  ];

  const assets = ["XAU/USD (Gold)", "EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD"];
  const indicators = [
    "RSI",
    "MACD",
    "Support/Resistance",
    "Pullback Patterns",
    "Breakout Patterns",
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-accent/10" />
        <div className="relative max-w-7xl mx-auto text-center">
          <Badge
            variant="outline"
            className="mb-6 text-primary border-primary/20"
          >
            <Lightbulb className="w-4 h-4 mr-2" />
            AI-Powered Trading Optimization
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-foreground via-primary to-accent bg-clip-text text-transparent">
            AI Trader Optimizer
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-4 max-w-3xl mx-auto">
            Transform your manual Forex & Gold trading strategies into
          </p>
          <p className="text-xl md:text-2xl text-muted-foreground mb-8 max-w-3xl mx-auto">
            <span className="text-primary font-semibold">backtested</span>,{" "}
            <span className="text-accent font-semibold">optimized</span>, and{" "}
            <span className="text-trading-green-500 font-semibold">
              automated
            </span>{" "}
            systems
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link to="/dashboard">
              <Button
                size="lg"
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                Start Optimizing
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link to="/backtest">
              <Button size="lg" variant="outline">
                View Demo Results
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-card/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            {stats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <Card key={index} className="text-center border-border/50">
                  <CardContent className="pt-6">
                    <Icon className={`w-8 h-8 mx-auto mb-2 ${stat.color}`} />
                    <div className="text-2xl font-bold mb-1">{stat.value}</div>
                    <div className="text-sm text-muted-foreground">
                      {stat.label}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Complete Trading Intelligence
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              From manual strategy analysis to fully optimized automated trading
              systems
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card
                  key={index}
                  className="border-border/50 hover:border-primary/20 transition-colors"
                >
                  <CardHeader>
                    <Icon className={`w-10 h-10 ${feature.color} mb-2`} />
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                    <CardDescription className="text-muted-foreground">
                      {feature.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Trading Setup Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-card/30">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold mb-6">
                Your Trading Setup, Optimized
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                We've validated your complete trading infrastructure. Now let AI
                take it to the next level.
              </p>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-trading-green-500" />
                  <span>MT5 journal data converted and analyzed</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-trading-green-500" />
                  <span>XGBoost predictive model implemented</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-trading-green-500" />
                  <span>Money management system validated</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-trading-green-500" />
                  <span>Semi-automated execution ready</span>
                </div>
              </div>
            </div>
            <div className="space-y-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg">Supported Assets</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {assets.map((asset, index) => (
                      <Badge key={index} variant="secondary">
                        {asset}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg">
                    Technical Indicators
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {indicators.map((indicator, index) => (
                      <Badge key={index} variant="outline">
                        {indicator}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Optimize Your Trading?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Transform your intuitive manual system into a backtested, robust,
            and pilotable AI trading system.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/dashboard">
              <Button size="lg" className="bg-primary hover:bg-primary/90">
                Launch AI Optimizer
                <Brain className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link to="/backtest">
              <Button size="lg" variant="outline">
                View Backtest Results
                <BarChart3 className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

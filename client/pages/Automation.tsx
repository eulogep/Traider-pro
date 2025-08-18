import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Zap,
  Play,
  Pause,
  Square,
  Settings,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  Brain,
  Bell,
  Smartphone,
  Mail,
  Database,
  BarChart3,
  RefreshCw,
  Power,
  Eye,
  Edit,
  Trash2,
} from "lucide-react";

export default function Automation() {
  const [botStatus, setBotStatus] = useState<"running" | "paused" | "stopped">("stopped");
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);
  const [maxRisk, setMaxRisk] = useState([2]);
  const [emergencyStop, setEmergencyStop] = useState(false);

  const activeBots = [
    {
      id: 1,
      name: "XAU/USD Scalper",
      strategy: "RSI + MACD",
      status: "running",
      profit: "+$1,247.80",
      trades: 23,
      uptime: "2h 34m",
      risk: "Low"
    },
    {
      id: 2,
      name: "EUR/USD Trend",
      strategy: "MA Crossover",
      status: "paused",
      profit: "+$892.40",
      trades: 15,
      uptime: "5h 12m",
      risk: "Medium"
    },
    {
      id: 3,
      name: "Multi-Asset AI",
      strategy: "AI Enhanced",
      status: "running",
      profit: "+$2,156.30",
      trades: 41,
      uptime: "8h 45m",
      risk: "Medium"
    }
  ];

  const recentActions = [
    { time: "14:23", action: "BUY XAU/USD", amount: "0.1", profit: "+$45.20", status: "closed" },
    { time: "14:15", action: "SELL EUR/USD", amount: "0.5", profit: "+$23.80", status: "closed" },
    { time: "14:08", action: "BUY GBP/USD", amount: "0.3", profit: "Running", status: "open" },
    { time: "13:55", action: "SELL XAU/USD", amount: "0.2", profit: "-$12.40", status: "closed" },
    { time: "13:42", action: "BUY USD/JPY", amount: "1.0", profit: "+$67.90", status: "closed" },
  ];

  const safetyRules = [
    { name: "Daily Loss Limit", value: "$500", enabled: true },
    { name: "Maximum Open Positions", value: "5", enabled: true },
    { name: "Risk per Trade", value: "2%", enabled: true },
    { name: "Trading Hours", value: "06:00-22:00 GMT", enabled: true },
    { name: "News Event Filter", value: "High Impact", enabled: true },
    { name: "Market Volatility Filter", value: ">3%", enabled: false },
  ];

  const toggleBotStatus = () => {
    if (botStatus === "running") {
      setBotStatus("paused");
    } else if (botStatus === "paused") {
      setBotStatus("running");
    } else {
      setBotStatus("running");
    }
  };

  const stopBot = () => {
    setBotStatus("stopped");
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Zap className="w-8 h-8 mr-3 text-accent" />
              Trading Automation
            </h1>
            <p className="text-muted-foreground">Semi-automated trading with manual validation</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={
              botStatus === "running" ? "default" :
              botStatus === "paused" ? "secondary" :
              "outline"
            } className={
              botStatus === "running" ? "text-trading-green-500 border-trading-green-500" :
              botStatus === "paused" ? "text-accent border-accent" :
              ""
            }>
              <div className={`w-2 h-2 rounded-full mr-2 ${
                botStatus === "running" ? "bg-trading-green-500 animate-pulse" :
                botStatus === "paused" ? "bg-accent" :
                "bg-muted-foreground"
              }`} />
              {botStatus.charAt(0).toUpperCase() + botStatus.slice(1)}
            </Badge>
            <Button
              onClick={toggleBotStatus}
              variant={botStatus === "running" ? "secondary" : "default"}
              className={botStatus === "running" ? "" : "bg-primary hover:bg-primary/90"}
            >
              {botStatus === "running" ? (
                <>
                  <Pause className="w-4 h-4 mr-2" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Start
                </>
              )}
            </Button>
            <Button
              onClick={stopBot}
              variant="destructive"
              size="sm"
              disabled={botStatus === "stopped"}
            >
              <Square className="w-4 h-4 mr-2" />
              Stop
            </Button>
          </div>
        </div>

        {/* Emergency Controls */}
        {emergencyStop && (
          <Card className="border-destructive bg-destructive/10">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <AlertTriangle className="w-6 h-6 text-destructive" />
                  <div>
                    <h3 className="font-semibold text-destructive">Emergency Stop Activated</h3>
                    <p className="text-sm text-muted-foreground">All automated trading has been halted</p>
                  </div>
                </div>
                <Button
                  onClick={() => setEmergencyStop(false)}
                  variant="outline"
                  size="sm"
                >
                  Resume
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="control" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="control">Control</TabsTrigger>
            <TabsTrigger value="bots">Bots</TabsTrigger>
            <TabsTrigger value="safety">Safety</TabsTrigger>
            <TabsTrigger value="notifications">Alerts</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
          </TabsList>

          {/* Control Tab */}
          <TabsContent value="control" className="space-y-6">
            <div className="grid lg:grid-cols-3 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Settings className="w-5 h-5 mr-2" />
                    Main Controls
                  </CardTitle>
                  <CardDescription>Primary automation settings</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Auto Trading</Label>
                      <p className="text-sm text-muted-foreground">Enable fully automated trading</p>
                    </div>
                    <Switch checked={autoTradeEnabled} onCheckedChange={setAutoTradeEnabled} />
                  </div>

                  <div className="space-y-2">
                    <Label>Trading Mode</Label>
                    <Select defaultValue="semi-auto">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="manual">Manual Only</SelectItem>
                        <SelectItem value="semi-auto">Semi-Automated</SelectItem>
                        <SelectItem value="full-auto">Fully Automated</SelectItem>
                        <SelectItem value="signal-only">Signals Only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Maximum Risk per Trade: {maxRisk[0]}%</Label>
                    <Slider
                      value={maxRisk}
                      onValueChange={setMaxRisk}
                      max={10}
                      min={0.1}
                      step={0.1}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Active Strategy</Label>
                    <Select defaultValue="ai-enhanced">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ai-enhanced">AI Enhanced</SelectItem>
                        <SelectItem value="rsi-macd">RSI + MACD</SelectItem>
                        <SelectItem value="breakout">Breakout Strategy</SelectItem>
                        <SelectItem value="scalping">Scalping</SelectItem>
                        <SelectItem value="trend-following">Trend Following</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    onClick={() => setEmergencyStop(true)}
                    variant="destructive"
                    className="w-full"
                  >
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Emergency Stop
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <BarChart3 className="w-5 h-5 mr-2" />
                    Performance Today
                  </CardTitle>
                  <CardDescription>Real-time automation metrics</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Profit</p>
                      <p className="text-lg font-bold text-trading-green-500">+$2,347.80</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Trades</p>
                      <p className="text-lg font-bold">47</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Win Rate</p>
                      <p className="text-lg font-bold text-primary">82.3%</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Active Bots</p>
                      <p className="text-lg font-bold">3</p>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-border">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">System Load</span>
                        <span>67%</span>
                      </div>
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div className="bg-primary h-2 rounded-full" style={{ width: "67%" }}></div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    Recent Actions
                  </CardTitle>
                  <CardDescription>Latest automated trades</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {recentActions.slice(0, 5).map((action, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <div className="flex items-center space-x-2">
                          <span className="text-muted-foreground">{action.time}</span>
                          <span className="font-medium">{action.action}</span>
                          <Badge variant="outline" className="text-xs">{action.amount}</Badge>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={action.status === "open" ? "secondary" : "outline"} className="text-xs">
                            {action.status}
                          </Badge>
                          <span className={`font-medium ${
                            action.profit.includes('+') ? 'text-trading-green-500' :
                            action.profit.includes('-') ? 'text-trading-red-500' :
                            'text-muted-foreground'
                          }`}>
                            {action.profit}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Bots Tab */}
          <TabsContent value="bots" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">Active Trading Bots</h2>
              <Button className="bg-primary hover:bg-primary/90">
                <Zap className="w-4 h-4 mr-2" />
                Create New Bot
              </Button>
            </div>

            <div className="grid gap-4">
              {activeBots.map((bot) => (
                <Card key={bot.id} className="border-border/50">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className={`w-3 h-3 rounded-full ${
                          bot.status === 'running' ? 'bg-trading-green-500 animate-pulse' :
                          bot.status === 'paused' ? 'bg-accent' :
                          'bg-muted-foreground'
                        }`} />
                        <div>
                          <h3 className="font-semibold">{bot.name}</h3>
                          <p className="text-sm text-muted-foreground">{bot.strategy}</p>
                        </div>
                        <Badge variant={
                          bot.status === 'running' ? 'default' :
                          bot.status === 'paused' ? 'secondary' :
                          'outline'
                        }>
                          {bot.status}
                        </Badge>
                        <Badge variant="outline" className={
                          bot.risk === 'Low' ? 'border-trading-green-500 text-trading-green-500' :
                          bot.risk === 'Medium' ? 'border-accent text-accent' :
                          'border-trading-red-500 text-trading-red-500'
                        }>
                          {bot.risk} Risk
                        </Badge>
                      </div>
                      
                      <div className="flex items-center space-x-6">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Profit</p>
                          <p className="font-semibold text-trading-green-500">{bot.profit}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Trades</p>
                          <p className="font-semibold">{bot.trades}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Uptime</p>
                          <p className="font-semibold">{bot.uptime}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button variant="outline" size="sm">
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Safety Tab */}
          <TabsContent value="safety" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Shield className="w-5 h-5 mr-2" />
                  Safety Rules & Risk Management
                </CardTitle>
                <CardDescription>Configure automated safety mechanisms</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {safetyRules.map((rule, index) => (
                    <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-border/30">
                      <div className="flex items-center space-x-3">
                        <Switch checked={rule.enabled} />
                        <div>
                          <h4 className="font-medium">{rule.name}</h4>
                          <p className="text-sm text-muted-foreground">{rule.value}</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Emergency Procedures</CardTitle>
                  <CardDescription>Automated responses to critical situations</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Market Crash Response</Label>
                    <Select defaultValue="close-all">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="close-all">Close All Positions</SelectItem>
                        <SelectItem value="reduce-risk">Reduce Risk Level</SelectItem>
                        <SelectItem value="pause-trading">Pause Trading</SelectItem>
                        <SelectItem value="notify-only">Notify Only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Connection Loss Action</Label>
                    <Select defaultValue="safe-mode">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="safe-mode">Enter Safe Mode</SelectItem>
                        <SelectItem value="continue">Continue Trading</SelectItem>
                        <SelectItem value="stop-all">Stop All Trading</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Daily Loss Threshold</Label>
                    <Input type="number" defaultValue="1000" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle>Monitoring Settings</CardTitle>
                  <CardDescription>System health and performance monitoring</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Real-time Monitoring</Label>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label>Performance Alerts</Label>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label>Risk Level Warnings</Label>
                    <Switch defaultChecked />
                  </div>

                  <div className="space-y-2">
                    <Label>Check Interval</Label>
                    <Select defaultValue="1min">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="30sec">30 Seconds</SelectItem>
                        <SelectItem value="1min">1 Minute</SelectItem>
                        <SelectItem value="5min">5 Minutes</SelectItem>
                        <SelectItem value="15min">15 Minutes</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Bell className="w-5 h-5 mr-2" />
                    Alert Settings
                  </CardTitle>
                  <CardDescription>Configure notification preferences</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Trade Confirmations</Label>
                        <p className="text-sm text-muted-foreground">Notify on each trade execution</p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Profit/Loss Alerts</Label>
                        <p className="text-sm text-muted-foreground">Alert on significant P&L changes</p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>System Errors</Label>
                        <p className="text-sm text-muted-foreground">Immediate error notifications</p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Market Events</Label>
                        <p className="text-sm text-muted-foreground">Economic news and events</p>
                      </div>
                      <Switch />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Smartphone className="w-5 h-5 mr-2" />
                    Delivery Methods
                  </CardTitle>
                  <CardDescription>How you want to receive alerts</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Smartphone className="w-4 h-4" />
                        <Label>Mobile Push</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Mail className="w-4 h-4" />
                        <Label>Email</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Bell className="w-4 h-4" />
                        <Label>In-App</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Smartphone className="w-4 h-4" />
                        <Label>Telegram</Label>
                      </div>
                      <Switch />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Email Address</Label>
                    <Input type="email" placeholder="your@email.com" />
                  </div>

                  <div className="space-y-2">
                    <Label>Telegram Bot Token</Label>
                    <Input type="password" placeholder="Enter bot token" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Database className="w-5 h-5 mr-2" />
                  System Logs
                </CardTitle>
                <CardDescription>Detailed automation activity logs</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {[
                    { time: "14:23:45", level: "INFO", message: "Trade executed: BUY XAU/USD 0.1 lots at 1985.50" },
                    { time: "14:23:12", level: "INFO", message: "Signal generated: RSI oversold on XAU/USD" },
                    { time: "14:22:55", level: "WARNING", message: "High volatility detected on EUR/USD" },
                    { time: "14:22:30", level: "INFO", message: "Position closed: SELL EUR/USD +$23.80 profit" },
                    { time: "14:21:45", level: "INFO", message: "Risk check passed for new trade" },
                    { time: "14:21:12", level: "ERROR", message: "Connection timeout to MT5 server" },
                    { time: "14:20:55", level: "INFO", message: "Connection restored to MT5 server" },
                    { time: "14:20:30", level: "INFO", message: "AI model prediction: 87% confidence BUY signal" },
                    { time: "14:19:45", level: "INFO", message: "Safety check: Daily risk limit at 45%" },
                    { time: "14:19:12", level: "INFO", message: "Market analysis completed" },
                  ].map((log, index) => (
                    <div key={index} className="flex items-start space-x-3 text-sm p-2 rounded">
                      <span className="text-muted-foreground font-mono">{log.time}</span>
                      <Badge variant={
                        log.level === 'ERROR' ? 'destructive' :
                        log.level === 'WARNING' ? 'secondary' :
                        'outline'
                      } className="text-xs">
                        {log.level}
                      </Badge>
                      <span className="flex-1">{log.message}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

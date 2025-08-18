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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Settings as SettingsIcon,
  Database,
  Shield,
  Bell,
  Palette,
  Globe,
  Download,
  Upload,
  RefreshCw,
  Save,
  Eye,
  EyeOff,
  CheckCircle,
  AlertTriangle,
  Smartphone,
  Mail,
  Key,
  Server,
  Monitor,
  Moon,
  Sun,
  Zap,
  Brain,
  Target,
  BarChart3,
  DollarSign,
} from "lucide-react";

export default function Settings() {
  const [showApiKey, setShowApiKey] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<
    "connected" | "disconnected" | "testing"
  >("connected");

  const testConnection = () => {
    setConnectionStatus("testing");
    setTimeout(() => {
      setConnectionStatus("connected");
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <SettingsIcon className="w-8 h-8 mr-3 text-primary" />
              System Settings
            </h1>
            <p className="text-muted-foreground">
              Configure your AI Trader Optimizer preferences
            </p>
          </div>
          <Button className="bg-primary hover:bg-primary/90">
            <Save className="w-4 h-4 mr-2" />
            Save Changes
          </Button>
        </div>

        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="trading">Trading</TabsTrigger>
            <TabsTrigger value="connections">Connections</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="backup">Backup</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Palette className="w-5 h-5 mr-2" />
                    Appearance
                  </CardTitle>
                  <CardDescription>
                    Customize the interface appearance
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Dark Mode</Label>
                      <p className="text-sm text-muted-foreground">
                        Use dark theme for better trading visibility
                      </p>
                    </div>
                    <Switch checked={darkMode} onCheckedChange={setDarkMode} />
                  </div>

                  <div className="space-y-2">
                    <Label>Color Theme</Label>
                    <Select defaultValue="professional">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="professional">
                          Professional (Default)
                        </SelectItem>
                        <SelectItem value="high-contrast">
                          High Contrast
                        </SelectItem>
                        <SelectItem value="colorblind">
                          Colorblind Friendly
                        </SelectItem>
                        <SelectItem value="minimal">Minimal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Chart Style</Label>
                    <Select defaultValue="candlestick">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="candlestick">Candlestick</SelectItem>
                        <SelectItem value="line">Line Chart</SelectItem>
                        <SelectItem value="bar">Bar Chart</SelectItem>
                        <SelectItem value="area">Area Chart</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Dashboard Layout</Label>
                    <Select defaultValue="grid">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="grid">Grid Layout</SelectItem>
                        <SelectItem value="list">List Layout</SelectItem>
                        <SelectItem value="compact">Compact View</SelectItem>
                        <SelectItem value="detailed">Detailed View</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Globe className="w-5 h-5 mr-2" />
                    Regional Settings
                  </CardTitle>
                  <CardDescription>
                    Configure regional preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label>Language</Label>
                    <Select defaultValue="en">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="fr">Français</SelectItem>
                        <SelectItem value="de">Deutsch</SelectItem>
                        <SelectItem value="es">Español</SelectItem>
                        <SelectItem value="ja">日本語</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Timezone</Label>
                    <Select defaultValue="utc">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="utc">UTC</SelectItem>
                        <SelectItem value="et">Eastern Time</SelectItem>
                        <SelectItem value="pt">Pacific Time</SelectItem>
                        <SelectItem value="gmt">GMT</SelectItem>
                        <SelectItem value="cet">
                          Central European Time
                        </SelectItem>
                        <SelectItem value="jst">Japan Standard Time</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Currency Display</Label>
                    <Select defaultValue="usd">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="usd">USD ($)</SelectItem>
                        <SelectItem value="eur">EUR (€)</SelectItem>
                        <SelectItem value="gbp">GBP (£)</SelectItem>
                        <SelectItem value="jpy">JPY (¥)</SelectItem>
                        <SelectItem value="cad">CAD (C$)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Number Format</Label>
                    <Select defaultValue="us">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="us">1,234.56 (US)</SelectItem>
                        <SelectItem value="eu">1.234,56 (EU)</SelectItem>
                        <SelectItem value="space">1 234,56 (Space)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Trading Tab */}
          <TabsContent value="trading" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Target className="w-5 h-5 mr-2" />
                    Default Trading Parameters
                  </CardTitle>
                  <CardDescription>
                    Set default values for new trades
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label>Default Risk per Trade (%)</Label>
                    <Input
                      type="number"
                      defaultValue="2"
                      min="0.1"
                      max="10"
                      step="0.1"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Default Stop Loss (pips)</Label>
                    <Input type="number" defaultValue="50" />
                  </div>

                  <div className="space-y-2">
                    <Label>Default Take Profit (pips)</Label>
                    <Input type="number" defaultValue="100" />
                  </div>

                  <div className="space-y-2">
                    <Label>Default Position Size</Label>
                    <Select defaultValue="auto">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto Calculate</SelectItem>
                        <SelectItem value="fixed">Fixed Lots</SelectItem>
                        <SelectItem value="percent">
                          Percentage of Balance
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Slippage Tolerance (pips)</Label>
                    <Input type="number" defaultValue="3" />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>One-Click Trading</Label>
                      <p className="text-sm text-muted-foreground">
                        Enable quick trade execution
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Brain className="w-5 h-5 mr-2" />
                    AI Enhancement Settings
                  </CardTitle>
                  <CardDescription>
                    Configure AI optimization preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>AI Signal Validation</Label>
                      <p className="text-sm text-muted-foreground">
                        Require AI confirmation for trades
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="space-y-2">
                    <Label>AI Confidence Threshold (%)</Label>
                    <Input type="number" defaultValue="75" min="50" max="95" />
                  </div>

                  <div className="space-y-2">
                    <Label>Optimization Frequency</Label>
                    <Select defaultValue="daily">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="realtime">Real-time</SelectItem>
                        <SelectItem value="hourly">Hourly</SelectItem>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                        <SelectItem value="manual">Manual Only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Model Selection</Label>
                    <Select defaultValue="auto">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto Select Best</SelectItem>
                        <SelectItem value="xgboost">XGBoost</SelectItem>
                        <SelectItem value="lstm">
                          LSTM Neural Network
                        </SelectItem>
                        <SelectItem value="ensemble">
                          Ensemble Methods
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Learning Mode</Label>
                      <p className="text-sm text-muted-foreground">
                        Allow AI to learn from your trades
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Connections Tab */}
          <TabsContent value="connections" className="space-y-6">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Database className="w-5 h-5 mr-2" />
                  Trading Platform Connections
                </CardTitle>
                <CardDescription>
                  Manage broker and platform integrations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border border-border/30">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          connectionStatus === "connected"
                            ? "bg-trading-green-500"
                            : connectionStatus === "testing"
                              ? "bg-accent animate-pulse"
                              : "bg-trading-red-500"
                        }`}
                      />
                      <div>
                        <h4 className="font-medium">MetaTrader 5</h4>
                        <p className="text-sm text-muted-foreground">
                          Primary trading platform
                        </p>
                      </div>
                      <Badge
                        variant={
                          connectionStatus === "connected"
                            ? "default"
                            : "secondary"
                        }
                      >
                        {connectionStatus}
                      </Badge>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={testConnection}
                        disabled={connectionStatus === "testing"}
                      >
                        {connectionStatus === "testing"
                          ? "Testing..."
                          : "Test Connection"}
                      </Button>
                      <Button variant="outline" size="sm">
                        Configure
                      </Button>
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h3 className="font-semibold">MT5 Configuration</h3>
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <Label>Server Address</Label>
                        <Input defaultValue="mt5.broker.com:443" />
                      </div>
                      <div className="space-y-2">
                        <Label>Account Number</Label>
                        <Input defaultValue="12345678" />
                      </div>
                      <div className="space-y-2">
                        <Label>Password</Label>
                        <div className="relative">
                          <Input
                            type={showApiKey ? "text" : "password"}
                            defaultValue="password123"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="absolute right-0 top-0 h-full px-3"
                            onClick={() => setShowApiKey(!showApiKey)}
                          >
                            {showApiKey ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">API Settings</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label>Enable Expert Advisors</Label>
                        <Switch defaultChecked />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label>Allow Automated Trading</Label>
                        <Switch defaultChecked />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label>Real-time Data Feed</Label>
                        <Switch defaultChecked />
                      </div>
                      <div className="space-y-2">
                        <Label>Update Frequency (ms)</Label>
                        <Input type="number" defaultValue="1000" />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Data Providers</CardTitle>
                <CardDescription>Configure market data sources</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid lg:grid-cols-3 gap-4">
                  {[
                    {
                      name: "Alpha Vantage",
                      status: "connected",
                      type: "Primary",
                    },
                    {
                      name: "Yahoo Finance",
                      status: "connected",
                      type: "Backup",
                    },
                    {
                      name: "Economic Calendar",
                      status: "disconnected",
                      type: "News",
                    },
                  ].map((provider, index) => (
                    <div
                      key={index}
                      className="p-3 rounded-lg border border-border/30"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">{provider.name}</h4>
                        <Badge
                          variant={
                            provider.status === "connected"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {provider.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        {provider.type}
                      </p>
                      <Button variant="outline" size="sm" className="w-full">
                        Configure
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Bell className="w-5 h-5 mr-2" />
                    Alert Preferences
                  </CardTitle>
                  <CardDescription>
                    Choose when and how to receive notifications
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Trade Execution</Label>
                        <p className="text-sm text-muted-foreground">
                          Notify when trades are executed
                        </p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Profit/Loss Targets</Label>
                        <p className="text-sm text-muted-foreground">
                          Alert when TP/SL is hit
                        </p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>AI Signals</Label>
                        <p className="text-sm text-muted-foreground">
                          Notify on AI trade recommendations
                        </p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>System Errors</Label>
                        <p className="text-sm text-muted-foreground">
                          Alert on system issues
                        </p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Market News</Label>
                        <p className="text-sm text-muted-foreground">
                          Economic events and news
                        </p>
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
                  <CardDescription>
                    Configure notification channels
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Bell className="w-4 h-4" />
                        <Label>In-App Notifications</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Mail className="w-4 h-4" />
                        <Label>Email Alerts</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Smartphone className="w-4 h-4" />
                        <Label>Push Notifications</Label>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label>Email Address</Label>
                      <Input type="email" defaultValue="trader@example.com" />
                    </div>

                    <div className="space-y-2">
                      <Label>Phone Number (SMS)</Label>
                      <Input type="tel" placeholder="+1 (555) 123-4567" />
                    </div>

                    <div className="space-y-2">
                      <Label>Telegram Bot Token</Label>
                      <Input type="password" placeholder="Enter bot token" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Shield className="w-5 h-5 mr-2" />
                    Account Security
                  </CardTitle>
                  <CardDescription>
                    Protect your trading account
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Two-Factor Authentication</Label>
                      <p className="text-sm text-muted-foreground">
                        Add extra security to your account
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="space-y-2">
                    <Label>Session Timeout (minutes)</Label>
                    <Select defaultValue="30">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15">15 minutes</SelectItem>
                        <SelectItem value="30">30 minutes</SelectItem>
                        <SelectItem value="60">1 hour</SelectItem>
                        <SelectItem value="240">4 hours</SelectItem>
                        <SelectItem value="never">Never</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>IP Whitelist</Label>
                      <p className="text-sm text-muted-foreground">
                        Restrict access to specific IP addresses
                      </p>
                    </div>
                    <Switch />
                  </div>

                  <div className="space-y-2">
                    <Label>Allowed IP Addresses</Label>
                    <Textarea
                      placeholder="192.168.1.1&#10;203.0.113.1&#10;198.51.100.1"
                      rows={3}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Key className="w-5 h-5 mr-2" />
                    API Keys & Tokens
                  </CardTitle>
                  <CardDescription>
                    Manage API access credentials
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="p-3 rounded-lg border border-border/30">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">Trading API Key</h4>
                        <Badge variant="default">Active</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        sk-trading-xxxxxxxxxxxxxxxx
                      </p>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">
                          Regenerate
                        </Button>
                        <Button variant="outline" size="sm">
                          Revoke
                        </Button>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg border border-border/30">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">Data Feed API Key</h4>
                        <Badge variant="default">Active</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        pk-data-xxxxxxxxxxxxxxxx
                      </p>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">
                          Regenerate
                        </Button>
                        <Button variant="outline" size="sm">
                          Revoke
                        </Button>
                      </div>
                    </div>
                  </div>

                  <Button className="w-full">
                    <Key className="w-4 h-4 mr-2" />
                    Generate New API Key
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Backup Tab */}
          <TabsContent value="backup" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Download className="w-5 h-5 mr-2" />
                    Data Backup
                  </CardTitle>
                  <CardDescription>
                    Backup your trading data and settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Automatic Backups</Label>
                      <p className="text-sm text-muted-foreground">
                        Regular automated backups
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="space-y-2">
                    <Label>Backup Frequency</Label>
                    <Select defaultValue="daily">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="hourly">Every Hour</SelectItem>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                        <SelectItem value="monthly">Monthly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Backup Location</Label>
                    <Select defaultValue="cloud">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cloud">Cloud Storage</SelectItem>
                        <SelectItem value="local">Local Storage</SelectItem>
                        <SelectItem value="both">Both</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3">
                    <Button className="w-full">
                      <Download className="w-4 h-4 mr-2" />
                      Create Backup Now
                    </Button>
                    <Button variant="outline" className="w-full">
                      <Upload className="w-4 h-4 mr-2" />
                      Restore from Backup
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <RefreshCw className="w-5 h-5 mr-2" />
                    System Maintenance
                  </CardTitle>
                  <CardDescription>
                    System cleanup and optimization
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">Clear Cache</h4>
                        <p className="text-sm text-muted-foreground">
                          Remove temporary files
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Clear
                      </Button>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">Optimize Database</h4>
                        <p className="text-sm text-muted-foreground">
                          Improve performance
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Optimize
                      </Button>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">Reset Settings</h4>
                        <p className="text-sm text-muted-foreground">
                          Restore default configuration
                        </p>
                      </div>
                      <Button variant="destructive" size="sm">
                        Reset
                      </Button>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <h4 className="font-medium">Export Settings</h4>
                    <p className="text-sm text-muted-foreground">
                      Download your configuration
                    </p>
                    <Button variant="outline" className="w-full">
                      <Download className="w-4 h-4 mr-2" />
                      Export Configuration
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

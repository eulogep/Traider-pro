import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMT5, useMT5Account } from "@/hooks/useMT5";
import {
  Database,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Eye,
  EyeOff,
} from "lucide-react";

export function MT5ConnectionButton() {
  const { connected, connecting, connect, disconnect, error, clearError } =
    useMT5();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [connectionForm, setConnectionForm] = useState({
    server: "mt5.demo-server.com:443",
    login: "12345678",
    password: "",
  });

  const handleConnect = async () => {
    try {
      clearError();
      await connect(connectionForm);
      setIsDialogOpen(false);
    } catch (error) {
      console.error("Connection failed:", error);
    }
  };

  const handleDisconnect = () => {
    disconnect();
    setIsDialogOpen(false);
  };

  return (
    <>
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogTrigger asChild>
          <Button
            variant={connected ? "outline" : "default"}
            size="sm"
            className={
              connected ? "border-trading-green-500 text-trading-green-500" : ""
            }
          >
            {connected ? (
              <>
                <Wifi className="w-4 h-4 mr-2" />
                Connected
              </>
            ) : connecting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 mr-2" />
                Connect MT5
              </>
            )}
          </Button>
        </DialogTrigger>

        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Database className="w-5 h-5 mr-2" />
              MT5 Connection
            </DialogTitle>
            <DialogDescription>
              {connected
                ? "Manage your MetaTrader 5 connection"
                : "Connect to your MetaTrader 5 account"}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {connected ? (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-trading-green-500" />
                <span className="font-medium">Connected to MT5</span>
              </div>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Server: {connectionForm.server}</p>
                <p>Login: {connectionForm.login}</p>
              </div>
              <Button
                onClick={handleDisconnect}
                variant="destructive"
                className="w-full"
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="server">MT5 Server</Label>
                <Input
                  id="server"
                  value={connectionForm.server}
                  onChange={(e) =>
                    setConnectionForm((prev) => ({
                      ...prev,
                      server: e.target.value,
                    }))
                  }
                  placeholder="mt5.broker.com:443"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="login">Login</Label>
                <Input
                  id="login"
                  value={connectionForm.login}
                  onChange={(e) =>
                    setConnectionForm((prev) => ({
                      ...prev,
                      login: e.target.value,
                    }))
                  }
                  placeholder="Account number"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={connectionForm.password}
                    onChange={(e) =>
                      setConnectionForm((prev) => ({
                        ...prev,
                        password: e.target.value,
                      }))
                    }
                    placeholder="Account password"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              <Button
                onClick={handleConnect}
                disabled={connecting}
                className="w-full"
              >
                {connecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  "Connect"
                )}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export function MT5StatusIndicator() {
  const { connected } = useMT5();

  if (!connected) {
    return (
      <Badge
        variant="outline"
        className="text-muted-foreground border-muted-foreground"
      >
        <WifiOff className="w-3 h-3 mr-1" />
        Offline
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="text-trading-green-500 border-trading-green-500"
    >
      <div className="w-2 h-2 bg-trading-green-500 rounded-full mr-2 animate-pulse" />
      MT5 Live
    </Badge>
  );
}

export function MT5AccountSummary() {
  const { account, summary, connected } = useMT5Account();

  if (!connected || !account) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center text-muted-foreground">
            <Database className="w-5 h-5 mr-2" />
            MT5 Account
          </CardTitle>
          <CardDescription>
            Connect to MT5 to view account information
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Database className="w-5 h-5 mr-2" />
          MT5 Account - {account.name}
        </CardTitle>
        <CardDescription>
          {account.company} • {account.server}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Balance</p>
            <p className="text-lg font-bold">
              ${summary.balance.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Equity</p>
            <p className="text-lg font-bold">
              ${summary.equity.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Free Margin</p>
            <p className="text-lg font-bold">
              ${summary.freeMargin.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Margin Level</p>
            <p className="text-lg font-bold">
              {summary.marginLevel.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Open P&L</p>
            <p
              className={`text-lg font-bold ${
                summary.profit >= 0
                  ? "text-trading-green-500"
                  : "text-trading-red-500"
              }`}
            >
              {summary.profit >= 0 ? "+" : ""}${summary.profit.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Positions</p>
            <p className="text-lg font-bold">{summary.openPositions}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMT5, useMT5Symbol } from "@/hooks/useMT5";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  X,
  Play,
  Pause,
  BarChart3,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";

export function MT5QuickTrade({ symbol = "XAUUSD" }: { symbol?: string }) {
  const { connected, placeOrder, error } = useMT5();
  const { symbol: symbolData } = useMT5Symbol(symbol);
  const [volume, setVolume] = useState("0.1");
  const [sl, setSl] = useState("");
  const [tp, setTp] = useState("");
  const [isOrderDialogOpen, setIsOrderDialogOpen] = useState(false);
  const [orderType, setOrderType] = useState<"BUY" | "SELL">("BUY");

  const handleQuickTrade = async (type: "BUY" | "SELL") => {
    if (!connected || !symbolData) return;

    try {
      await placeOrder({
        symbol: symbolData.symbol,
        type,
        volume: parseFloat(volume),
        sl: sl ? parseFloat(sl) : undefined,
        tp: tp ? parseFloat(tp) : undefined,
        comment: "Quick Trade",
      });
      setIsOrderDialogOpen(false);
    } catch (error) {
      console.error("Trade failed:", error);
    }
  };

  if (!connected) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Quick Trade</CardTitle>
          <CardDescription>Connect to MT5 to start trading</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!symbolData) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Quick Trade</CardTitle>
          <CardDescription>Loading symbol data...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Quick Trade - {symbolData.symbol}</span>
          <div className="flex items-center space-x-2">
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Bid</p>
              <p className="font-mono text-sm">
                {symbolData.bid.toFixed(symbolData.digits)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Ask</p>
              <p className="font-mono text-sm">
                {symbolData.ask.toFixed(symbolData.digits)}
              </p>
            </div>
          </div>
        </CardTitle>
        <CardDescription>
          Spread: {symbolData.spread} | Change:
          <span
            className={
              symbolData.change >= 0
                ? "text-trading-green-500"
                : "text-trading-red-500"
            }
          >
            {symbolData.change >= 0 ? "+" : ""}
            {symbolData.changePercent.toFixed(3)}%
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Dialog open={isOrderDialogOpen} onOpenChange={setIsOrderDialogOpen}>
            <DialogTrigger asChild>
              <Button
                className="bg-trading-green-500 hover:bg-trading-green-600 text-white"
                onClick={() => setOrderType("BUY")}
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                BUY {symbolData.ask.toFixed(symbolData.digits)}
              </Button>
            </DialogTrigger>
            <DialogTrigger asChild>
              <Button
                variant="destructive"
                onClick={() => setOrderType("SELL")}
              >
                <TrendingDown className="w-4 h-4 mr-2" />
                SELL {symbolData.bid.toFixed(symbolData.digits)}
              </Button>
            </DialogTrigger>

            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {orderType} {symbolData.symbol}
                </DialogTitle>
                <DialogDescription>
                  Execute at{" "}
                  {orderType === "BUY" ? symbolData.ask : symbolData.bid}
                </DialogDescription>
              </DialogHeader>

              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Volume (lots)</Label>
                  <Input
                    value={volume}
                    onChange={(e) => setVolume(e.target.value)}
                    placeholder="0.1"
                    type="number"
                    step="0.01"
                    min="0.01"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Stop Loss</Label>
                    <Input
                      value={sl}
                      onChange={(e) => setSl(e.target.value)}
                      placeholder="Optional"
                      type="number"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Take Profit</Label>
                    <Input
                      value={tp}
                      onChange={(e) => setTp(e.target.value)}
                      placeholder="Optional"
                      type="number"
                      step="0.01"
                    />
                  </div>
                </div>

                <Button
                  onClick={() => handleQuickTrade(orderType)}
                  className="w-full"
                  variant={orderType === "BUY" ? "default" : "destructive"}
                >
                  Execute {orderType} Order
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
}

export function MT5Positions() {
  const { positions, closePosition, connected } = useMT5();

  if (!connected) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>Connect to MT5 to view positions</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const handleClosePosition = async (ticket: number) => {
    try {
      await closePosition(ticket);
    } catch (error) {
      console.error("Failed to close position:", error);
    }
  };

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center">
          <BarChart3 className="w-5 h-5 mr-2" />
          Open Positions ({positions.length})
        </CardTitle>
        <CardDescription>Current trading positions</CardDescription>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">
            No open positions
          </p>
        ) : (
          <div className="space-y-3">
            {positions.map((position) => (
              <div
                key={position.ticket}
                className="flex items-center justify-between p-3 rounded-lg border border-border/30"
              >
                <div className="flex items-center space-x-3">
                  <Badge
                    variant={position.type === "BUY" ? "default" : "secondary"}
                  >
                    {position.type}
                  </Badge>
                  <div>
                    <p className="font-medium">{position.symbol}</p>
                    <p className="text-sm text-muted-foreground">
                      {position.volume} lots @ {position.openPrice.toFixed(5)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className={`font-medium ${
                      position.profit >= 0
                        ? "text-trading-green-500"
                        : "text-trading-red-500"
                    }`}
                  >
                    {position.profit >= 0 ? "+" : ""}$
                    {position.profit.toFixed(2)}
                  </p>
                  <div className="flex items-center space-x-2">
                    <p className="text-sm text-muted-foreground">
                      {position.currentPrice.toFixed(5)}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleClosePosition(position.ticket)}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function MT5MarketWatch() {
  const { symbols, connected } = useMT5();
  const [selectedSymbols] = useState(["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]);

  if (!connected) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Market Watch</CardTitle>
          <CardDescription>Connect to MT5 to view live prices</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const watchedSymbols = symbols.filter((s) =>
    selectedSymbols.includes(s.symbol),
  );

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Market Watch
        </CardTitle>
        <CardDescription>Live market prices</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {watchedSymbols.map((symbol) => (
            <div
              key={symbol.symbol}
              className="flex items-center justify-between p-3 rounded-lg border border-border/30"
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`w-2 h-2 rounded-full animate-pulse ${
                    symbol.change >= 0
                      ? "bg-trading-green-500"
                      : "bg-trading-red-500"
                  }`}
                />
                <span className="font-medium">{symbol.symbol}</span>
              </div>
              <div className="text-right">
                <div className="flex items-center space-x-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Bid</p>
                    <p className="font-mono text-sm">
                      {symbol.bid.toFixed(symbol.digits)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Ask</p>
                    <p className="font-mono text-sm">
                      {symbol.ask.toFixed(symbol.digits)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Change</p>
                    <p
                      className={`text-sm font-medium ${
                        symbol.change >= 0
                          ? "text-trading-green-500"
                          : "text-trading-red-500"
                      }`}
                    >
                      {symbol.change >= 0 ? "+" : ""}
                      {symbol.changePercent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function MT5TradeHistory() {
  const { tradeHistory, connected } = useMT5();

  if (!connected) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>
            Connect to MT5 to view trade history
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Clock className="w-5 h-5 mr-2" />
          Trade History
        </CardTitle>
        <CardDescription>Recent completed trades</CardDescription>
      </CardHeader>
      <CardContent>
        {tradeHistory.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">
            No trade history
          </p>
        ) : (
          <div className="space-y-3">
            {tradeHistory.slice(0, 10).map((trade) => (
              <div
                key={trade.ticket}
                className="flex items-center justify-between p-3 rounded-lg border border-border/30"
              >
                <div className="flex items-center space-x-3">
                  <Badge
                    variant={trade.type === "BUY" ? "default" : "secondary"}
                  >
                    {trade.type}
                  </Badge>
                  <div>
                    <p className="font-medium">{trade.symbol}</p>
                    <p className="text-sm text-muted-foreground">
                      {trade.volume} lots •{" "}
                      {new Date(trade.openTime).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className={`font-medium ${
                      trade.profit >= 0
                        ? "text-trading-green-500"
                        : "text-trading-red-500"
                    }`}
                  >
                    {trade.profit >= 0 ? "+" : ""}${trade.profit.toFixed(2)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {trade.openPrice.toFixed(5)} →{" "}
                    {trade.closePrice?.toFixed(5)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function MT5TradingPanel() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="trade" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trade">Trade</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="market">Market</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="trade" className="space-y-4">
          <MT5QuickTrade />
        </TabsContent>

        <TabsContent value="positions" className="space-y-4">
          <MT5Positions />
        </TabsContent>

        <TabsContent value="market" className="space-y-4">
          <MT5MarketWatch />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <MT5TradeHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
}

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MT5AccountSummary } from "@/components/MT5Connection";
import { MT5TradingPanel } from "@/components/MT5Trading";
import { MarketOverview } from "@/components/TradingChart";
import { useMT5 } from "@/hooks/useMT5";
import {
  TrendingUp,
  Activity,
  AlertTriangle,
  Wifi,
  WifiOff,
} from "lucide-react";

export default function Trading() {
  const { connected } = useMT5();

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <TrendingUp className="w-8 h-8 mr-3 text-primary" />
              MT5 Trading Terminal
            </h1>
            <p className="text-muted-foreground">
              {connected
                ? "Connected to MetaTrader 5 - Live trading active"
                : "Connect to MetaTrader 5 to start live trading"}
            </p>
          </div>
        </div>

        {/* Connection Status */}
        {!connected && (
          <Card className="border-accent/50 bg-accent/10">
            <CardContent className="p-4">
              <div className="flex items-center space-x-3">
                <WifiOff className="w-6 h-6 text-accent" />
                <div>
                  <h3 className="font-semibold">MT5 Not Connected</h3>
                  <p className="text-sm text-muted-foreground">
                    Connect to your MetaTrader 5 account to access live trading
                    features
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Account Summary */}
          <div className="lg:col-span-1">
            <MT5AccountSummary />
          </div>

          {/* Market Overview */}
          <div className="lg:col-span-2">
            <MarketOverview />
          </div>
        </div>

        {/* Trading Panel */}
        <MT5TradingPanel />

        {/* Risk Warning */}
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-6 h-6 text-destructive mt-1 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-destructive">Risk Warning</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Trading forex and CFDs involves significant risk of loss and
                  may not be suitable for all investors. Past performance is not
                  indicative of future results. Please ensure you fully
                  understand the risks and seek independent advice if necessary.
                  Only trade with money you can afford to lose.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

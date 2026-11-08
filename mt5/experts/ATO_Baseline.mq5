//+------------------------------------------------------------------+
//| ATO_Baseline — the illustrative baseline of AI Trader Optimizer   |
//| (strategies/baseline/ema_trend_3bars.v1.0.0.yaml), for the        |
//| Strategy Tester ONLY: independent check of the Python engine.     |
//| Its orders are simulated by the tester. It refuses to start on a  |
//| chart, and re-checks the tester flag before every order.          |
//| Same rules as the engine: signal on the CLOSED bar, entry at the  |
//| next open, session on the ENTRY bar, risk % of equity, limits.    |
//+------------------------------------------------------------------+
#property copyright "AI Trader Optimizer — simulation only"
#property version   "1.00"
#include <Trade\Trade.mqh>

input int    InpEmaFast      = 20;
input int    InpEmaSlow      = 50;
input int    InpAtrPeriod    = 14;    // simple average of the True Range (atr_method: sma)
input double InpSlAtrMult    = 1.5;
input double InpRR           = 1.5;
input int    InpWarmupBars   = 50;
input double InpRiskPct      = 0.25;
input double InpMaxDailyPct  = 1.0;
input double InpMaxDdPct     = 10.0;
input int    InpMaxTradesDay = 2;
input int    InpMaxLossesDay = 2;
input int    InpSessionStart = 720;   // minutes UTC of the ENTRY bar (12:00)
input int    InpSessionEnd   = 1020;  // minutes UTC (17:00)
input string InpSignalsFile  = "ATO\\baseline_decisions.csv"; // file in Terminal/Common/Files

CTrade   g_trade;
int      g_log = INVALID_HANDLE;
datetime g_last = 0, g_prev_time = 0;
long     g_bars = 0;
double   g_ema_f = 0, g_ema_s = 0, g_prev_close = 0, g_tr[];
int      g_col1 = 0, g_col2 = 0;
int      g_day = -1, g_trades_day = 0, g_losses_day = 0;
double   g_day_start = 0, g_day_pnl = 0, g_peak = 0, g_balance = 0;
bool     g_halted = false;

//--- MetaQuotes-Demo server clock = Europe/Athens (UTC+2, UTC+3 under EU summer time). Measured on the exported bars:
//--- with this zone the daily break ends at 18:00 New York on 162 of 166 days, including the US/EU changeover weeks.
bool IsEuSummer(const datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t, d);
   if(d.mon < 3 || d.mon > 10) return(false);
   if(d.mon > 3 && d.mon < 10) return(true);
   int last_sunday = 31 - (d.day_of_week + (31 - d.day)) % 7;  // March and October both have 31 days
   return(d.mon == 3 ? d.day >= last_sunday : d.day < last_sunday);
  }
datetime ServerToUtc(const datetime t) { return(t - (IsEuSummer(t) ? 3 : 2) * 3600); }

int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      Print("ATO_Baseline : réservé au Strategy Tester, démarrage refusé.");
      return(INIT_FAILED);
     }
   ArrayResize(g_tr, InpAtrPeriod);
   ArrayInitialize(g_tr, 0.0);
   g_balance = g_peak = g_day_start = AccountInfoDouble(ACCOUNT_BALANCE);
   g_trade.SetDeviationInPoints(1000);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_log = FileOpen(InpSignalsFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(g_log == INVALID_HANDLE)
      return(INIT_FAILED);
   FileWriteString(g_log, "signal_bar_server,signal_bar_utc,direction,outcome,reasons,lots,entry,sl,tp,spread\n");
   return(INIT_SUCCEEDED);
  }

void Log(const datetime t, const int d, const string out, const string why, const double lots,
         const double e, const double sl, const double tp, const double spread)
  {
   FileWriteString(g_log, StringFormat("%s,%s,%s,%s,%s,%.2f,%.2f,%.2f,%.2f,%.2f\n", TimeToString(t, TIME_DATE | TIME_SECONDS),
                   TimeToString(ServerToUtc(t), TIME_DATE | TIME_SECONDS), d > 0 ? "BUY" : "SELL", out, why, lots, e, sl, tp, spread));
  }

void OnTick()
  {
   MqlRates r[];
   if(CopyRates(_Symbol, PERIOD_M1, 0, 2, r) != 2 || r[0].time == g_last)
      return;
   g_last = r[0].time;                 // r[0] = bar just CLOSED, r[1] = bar opening now (entry bar)
   OnClosedBar(r[0], r[1].time);
  }

void OnClosedBar(const MqlRates &b, const datetime entry_time)
  {
   // indicators: same recursion as pandas ewm(span, adjust=False) and rolling mean of the True Range
   double af = 2.0 / (InpEmaFast + 1), as = 2.0 / (InpEmaSlow + 1);
   g_ema_f = g_bars == 0 ? b.close : af * b.close + (1 - af) * g_ema_f;
   g_ema_s = g_bars == 0 ? b.close : as * b.close + (1 - as) * g_ema_s;
   double tr = g_bars == 0 ? b.high - b.low : MathMax(b.high - b.low, MathMax(MathAbs(b.high - g_prev_close), MathAbs(b.low - g_prev_close)));
   g_tr[(int)(g_bars % InpAtrPeriod)] = tr;
   double atr = 0;
   if(g_bars + 1 >= InpAtrPeriod)
      for(int k = 0; k < InpAtrPeriod; k++) atr += g_tr[k] / InpAtrPeriod;
   int col = b.close > b.open ? 1 : (b.close < b.open ? -1 : 0);
   bool warm = g_bars < MathMax(MathMax(InpWarmupBars, InpEmaSlow), InpAtrPeriod);
   int sig = 0;
   if(!warm && atr > 0)
     {
      if(g_col2 == -1 && g_col1 == 1 && col == 1 && b.close > g_ema_f && g_ema_f > g_ema_s) sig = 1;
      if(g_col2 == 1 && g_col1 == -1 && col == -1 && b.close < g_ema_f && g_ema_f < g_ema_s) sig = -1;
     }
   g_col2 = g_col1; g_col1 = col; g_prev_close = b.close; g_bars++;

   // guardian state, in the same order as the engine
   datetime utc = ServerToUtc(entry_time);
   MqlDateTime u;
   TimeToStruct(utc, u);
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(bal != g_balance)
     {
      double net = bal - g_balance;
      g_day_pnl += net;
      if(net < 0) g_losses_day++;
      g_balance = bal;
      g_peak = MathMax(g_peak, bal);
      if(g_peak > 0 && (g_peak - bal) / g_peak * 100 >= InpMaxDdPct) g_halted = true;
     }
   if(u.day_of_year != g_day)
     {
      g_day = u.day_of_year;
      g_trades_day = 0; g_losses_day = 0; g_day_pnl = 0; g_day_start = bal;
     }
   if(sig == 0)
      return;

   string why = "";
   int minute = u.hour * 60 + u.min;
   if(u.day_of_week == 0 || u.day_of_week == 6) why += "NON_TRADING_DAY;";
   else if(minute < InpSessionStart || minute >= InpSessionEnd) why += "OUTSIDE_SESSION;";
   if(entry_time - b.time != 60) why += "DATA_INVALID;";
   if(g_halted) why += "MAX_DRAWDOWN_HALT;";
   if(PositionsTotal() > 0) why += "MAX_OPEN_POSITIONS;";
   if(g_trades_day >= InpMaxTradesDay) why += "MAX_TRADES_PER_DAY;";
   if(g_losses_day >= InpMaxLossesDay) why += "MAX_LOSSES_PER_DAY;";
   double daily_limit = g_day_start * InpMaxDailyPct / 100;
   if(g_day_pnl <= -daily_limit) why += "DAILY_LOSS_LIMIT;";

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spread = ask - bid, dist = atr * InpSlAtrMult;
   if(dist <= spread) why += "STOP_INSIDE_SPREAD;";
   double cs = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE), step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lots = MathFloor(bal * InpRiskPct / 100 / (dist * cs) / step + 1e-9) * step;
   lots = MathMin(lots, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   double planned = lots * dist * cs;
   if(lots < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) why += "SIZE_BELOW_MIN_LOT;";
   else
     {
      if(g_day_pnl - planned < -daily_limit - 1e-9) why += "DAILY_LOSS_BUDGET_INSUFFICIENT;";
      if(bal - planned < g_peak * (1 - InpMaxDdPct / 100) - 1e-9) why += "DRAWDOWN_BUDGET_INSUFFICIENT;";
     }
   double entry = sig > 0 ? ask : bid;
   double sl = NormalizeDouble(entry - sig * dist, _Digits), tp = NormalizeDouble(entry + sig * dist * InpRR, _Digits);
   if(why != "")
     {
      Log(b.time, sig, "REJECTED", why, 0, entry, sl, tp, spread);
      return;
     }
   if(!MQLInfoInteger(MQL_TESTER))   // second lock: no order can ever leave outside the tester
      return;
   bool ok = sig > 0 ? g_trade.Buy(lots, _Symbol, ask, sl, tp, "ATO-BASE") : g_trade.Sell(lots, _Symbol, bid, sl, tp, "ATO-BASE");
   if(ok) g_trades_day++;
   Log(b.time, sig, ok ? "ENTERED" : "SEND_FAILED", ok ? "" : IntegerToString(g_trade.ResultRetcode()), lots, entry, sl, tp, spread);
  }

void OnDeinit(const int reason)
  {
   if(g_log != INVALID_HANDLE)
      FileClose(g_log);
  }

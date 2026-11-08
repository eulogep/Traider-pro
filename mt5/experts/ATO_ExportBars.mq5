//+------------------------------------------------------------------+
//| ATO_ExportBars — historical bars, from the Strategy Tester, to a  |
//| CSV in the MT5 export format. Research tool of AI Trader Optimizer|
//| NO ORDER FUNCTION in this file. Refuses to run outside the tester.|
//+------------------------------------------------------------------+
#property copyright "AI Trader Optimizer — simulation only"
#property version   "1.00"

input string InpFile = "ATO\\bars.csv"; // file in Terminal/Common/Files

int      g_file = INVALID_HANDLE;
datetime g_last = 0;
long     g_rows = 0;

int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER))
     {
      Print("ATO_ExportBars : réservé au Strategy Tester, démarrage refusé.");
      return(INIT_FAILED);
     }
   g_file = FileOpen(InpFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(g_file == INVALID_HANDLE)
      return(INIT_FAILED);
   FileWriteString(g_file, "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n");
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   MqlRates r[];
   if(CopyRates(_Symbol, _Period, 1, 1, r) != 1 || r[0].time == g_last)
      return;
   g_last = r[0].time;
   FileWriteString(g_file, StringFormat("%s\t%s\t%s\t%s\t%s\t%s\t%I64d\t%I64d\t%d\n",
                   TimeToString(r[0].time, TIME_DATE), TimeToString(r[0].time, TIME_SECONDS),
                   DoubleToString(r[0].open, _Digits), DoubleToString(r[0].high, _Digits),
                   DoubleToString(r[0].low, _Digits), DoubleToString(r[0].close, _Digits),
                   r[0].tick_volume, r[0].real_volume, r[0].spread));
   g_rows++;
  }

void OnDeinit(const int reason)
  {
   if(g_file != INVALID_HANDLE)
      FileClose(g_file);
   PrintFormat("ATO_ExportBars : %I64d bougies écrites (point=%s, contrat=%s, devise=%s).", g_rows,
               DoubleToString(_Point, _Digits), DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE), 2),
               SymbolInfoString(_Symbol, SYMBOL_CURRENCY_PROFIT));
  }

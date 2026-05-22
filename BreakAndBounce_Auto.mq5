//+------------------------------------------------------------------+
//| BreakAndBounce_Auto.mq5                                          |
//| Converted from ProRealTime logic to MT5 Expert Advisor            |
//| Symbols: BTCUSD, XAUUSD-STD, XAUUSD-VIP                           |
//| Comment: BreakAndBounce auto                                      |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>

CTrade trade;

// === INPUTS ===
input string SymbolsToTrade = "BTCUSD,XAUUSD-STD,XAUUSD-VIP";
input double LotSize = 0.04;
input string TradeComment = "BreakAndBounce auto";

input int SessionStart = 153000;
input int SessionEnd   = 180000;
input int ExitTime     = 220000;

input double RiskReward = 3.0;
input double StopBufferMultiplier = 0.2;

input ulong MagicNumber = 7444181;
input int SlippagePoints = 30;

// === INTERNAL STATE ===
string Symbols[];
int Direction[];
datetime LastM5BarTime[];
datetime LastTradeBarTime[];

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   int count = StringSplit(SymbolsToTrade, ',', Symbols);

   if(count <= 0)
   {
      Print("No symbols found in SymbolsToTrade.");
      return INIT_FAILED;
   }

   ArrayResize(Direction, count);
   ArrayResize(LastM5BarTime, count);
   ArrayResize(LastTradeBarTime, count);

   for(int i = 0; i < count; i++)
   {
      Symbols[i] = Trim(Symbols[i]);
      Direction[i] = 0;
      LastM5BarTime[i] = 0;
      LastTradeBarTime[i] = 0;

      SymbolSelect(Symbols[i], true);
   }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePoints);

   Print("BreakAndBounce auto initialized.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert tick                                                       |
//+------------------------------------------------------------------+
void OnTick()
{
   for(int i = 0; i < ArraySize(Symbols); i++)
   {
      string symbol = Symbols[i];

      if(!SymbolSelect(symbol, true))
         continue;

      CloseAtEndOfDay(symbol);

      if(!IsNewM5Bar(symbol, i))
         continue;

      ProcessSymbol(symbol, i);
   }
}

//+------------------------------------------------------------------+
//| Main strategy logic                                               |
//+------------------------------------------------------------------+
void ProcessSymbol(string symbol, int index)
{
   MqlRates m5[3];
   ArraySetAsSeries(m5, true);

   if(CopyRates(symbol, PERIOD_M5, 0, 3, m5) < 3)
      return;

   MqlRates m15[3];
   ArraySetAsSeries(m15, true);

   if(CopyRates(symbol, PERIOD_M15, 0, 3, m15) < 3)
      return;

   MqlRates d1[3];
   ArraySetAsSeries(d1, true);

   if(CopyRates(symbol, PERIOD_D1, 0, 3, d1) < 3)
      return;

   // Previous daily high/low
   double prevHigh = d1[1].high;
   double prevLow  = d1[1].low;

   // Use last closed M15 candle for breakout detection
   double m15Close = m15[1].close;

   if(m15Close > prevHigh)
      Direction[index] = 1;

   if(m15Close < prevLow)
      Direction[index] = -1;

   // Reset direction at start of a new trading day
   static int lastDay[];
   if(ArraySize(lastDay) != ArraySize(Symbols))
      ArrayResize(lastDay, ArraySize(Symbols));

   MqlDateTime dt;
   TimeToStruct(m5[1].time, dt);

   if(lastDay[index] != dt.day)
   {
      Direction[index] = 0;
      lastDay[index] = dt.day;
   }

   int currentTime = TimeToHHMMSS(m5[1].time);

   if(currentTime < SessionStart || currentTime > SessionEnd)
      return;

   if(HasOpenPosition(symbol))
      return;

   // Use last closed M5 candle
   double open  = m5[1].open;
   double high  = m5[1].high;
   double low   = m5[1].low;
   double close = m5[1].close;

   double prevOpen  = m5[2].open;
   double prevClose = m5[2].close;

   double body = MathAbs(close - open);
   double candleRange = high - low;

   if(candleRange <= 0 || body <= 0)
      return;

   double upperWick = high - MathMax(open, close);
   double lowerWick = MathMin(open, close) - low;

   bool hammer = lowerWick > body * 2.0 && upperWick < body;
   bool invHammer = upperWick > body * 2.0 && lowerWick < body;

   bool bullEngulf =
      close > open &&
      prevClose < prevOpen &&
      close > prevOpen &&
      open < prevClose;

   bool bearEngulf =
      close < open &&
      prevClose > prevOpen &&
      close < prevOpen &&
      open > prevClose;

   bool retestLong = low <= prevHigh && close > prevHigh;
   bool retestShort = high >= prevLow && close < prevLow;

   // Avoid double entry on same candle
   if(LastTradeBarTime[index] == m5[1].time)
      return;

   // === LONG SETUP ===
   if(Direction[index] == 1 && retestLong)
   {
      if(hammer || bullEngulf)
      {
         double stopLoss = prevHigh - candleRange * StopBufferMultiplier;
         double risk = close - stopLoss;

         if(risk <= 0)
            return;

         double takeProfit = close + risk * RiskReward;

         OpenBuy(symbol, LotSize, stopLoss, takeProfit);
         LastTradeBarTime[index] = m5[1].time;
      }
   }

   // === SHORT SETUP ===
   if(Direction[index] == -1 && retestShort)
   {
      if(invHammer || bearEngulf)
      {
         double stopLoss = prevLow + candleRange * StopBufferMultiplier;
         double risk = stopLoss - close;

         if(risk <= 0)
            return;

         double takeProfit = close - risk * RiskReward;

         OpenSell(symbol, LotSize, stopLoss, takeProfit);
         LastTradeBarTime[index] = m5[1].time;
      }
   }
}

//+------------------------------------------------------------------+
//| Open buy                                                          |
//+------------------------------------------------------------------+
void OpenBuy(string symbol, double lots, double sl, double tp)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

   sl = NormalizePrice(symbol, sl);
   tp = NormalizePrice(symbol, tp);

   bool result = trade.Buy(lots, symbol, ask, sl, tp, TradeComment);

   if(result)
      Print("BUY opened: ", symbol, " Lot: ", lots, " SL: ", sl, " TP: ", tp);
   else
      Print("BUY failed: ", symbol, " Error: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Open sell                                                         |
//+------------------------------------------------------------------+
void OpenSell(string symbol, double lots, double sl, double tp)
{
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

   sl = NormalizePrice(symbol, sl);
   tp = NormalizePrice(symbol, tp);

   bool result = trade.Sell(lots, symbol, bid, sl, tp, TradeComment);

   if(result)
      Print("SELL opened: ", symbol, " Lot: ", lots, " SL: ", sl, " TP: ", tp);
   else
      Print("SELL failed: ", symbol, " Error: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Close positions after exit time                                   |
//+------------------------------------------------------------------+
void CloseAtEndOfDay(string symbol)
{
   int nowTime = TimeToHHMMSS(TimeCurrent());

   if(nowTime < ExitTime)
      return;

   if(!PositionSelect(symbol))
      return;

   ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);

   if(magic != MagicNumber)
      return;

   bool closed = trade.PositionClose(symbol);

   if(closed)
      Print("Position closed at end of day: ", symbol);
   else
      Print("Failed to close position: ", symbol, " Error: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Check if symbol already has open position from this EA             |
//+------------------------------------------------------------------+
bool HasOpenPosition(string symbol)
{
   if(!PositionSelect(symbol))
      return false;

   ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);

   if(magic == MagicNumber)
      return true;

   return false;
}

//+------------------------------------------------------------------+
//| Detect new M5 bar                                                  |
//+------------------------------------------------------------------+
bool IsNewM5Bar(string symbol, int index)
{
   datetime barTime = iTime(symbol, PERIOD_M5, 0);

   if(barTime == 0)
      return false;

   if(barTime != LastM5BarTime[index])
   {
      LastM5BarTime[index] = barTime;
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Convert time to HHMMSS integer                                     |
//+------------------------------------------------------------------+
int TimeToHHMMSS(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);

   return dt.hour * 10000 + dt.min * 100 + dt.sec;
}

//+------------------------------------------------------------------+
//| Normalize price                                                    |
//+------------------------------------------------------------------+
double NormalizePrice(string symbol, double price)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   return NormalizeDouble(price, digits);
}

//+------------------------------------------------------------------+
//| Trim helper                                                        |
//+------------------------------------------------------------------+
string Trim(string text)
{
   StringTrimLeft(text);
   StringTrimRight(text);
   return text;
}
//+------------------------------------------------------------------+
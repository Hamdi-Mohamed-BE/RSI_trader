//+------------------------------------------------------------------+
//| LTA Concepts - Volume Profile Retest EA                          |
//| Build target: MetaTrader 5 / MQL5                                |
//|                                                                  |
//| What it does:                                                    |
//| - Approximates Fixed Range / Daily / Weekly Volume Profile levels |
//|   using MT5 tick volume.                                         |
//| - Builds POC / VAH / VAL levels from previous day, previous week, |
//|   and a rolling fixed range.                                     |
//| - Trades double-wick rejection and optional internal-structure    |
//|   confirmation around those levels.                              |
//| - Runs on ALL sessions by default.                               |
//|                                                                  |
//| Important: TradingView FRVP data is not available inside native   |
//| MT5, so this EA calculates an approximation from broker candles   |
//| and tick_volume. Backtest first. No profit guarantee.             |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "LTA-style POC/VAH/VAL retest EA using MT5 tick-volume profile approximation."

#include <Trade/Trade.mqh>

CTrade trade;

//------------------------- ENUMS -----------------------------------
enum ENUM_RISK_MODE
{
   RISK_FIXED_LOT = 0,
   RISK_PERCENT_EQUITY = 1
};

enum ENUM_TREND_FILTER
{
   TREND_FILTER_OFF = 0,
   TREND_FILTER_EMA = 1
};

enum ENUM_ENTRY_MODEL
{
   ENTRY_DOUBLE_WICK_ONLY = 0,
   ENTRY_DOUBLE_WICK_PLUS_INTERNAL_BREAK = 1
};

//------------------------- INPUTS ----------------------------------
input group "Core"
input ulong              MagicNumber                 = 270324;
input ENUM_TIMEFRAMES    ProfileTF                   = PERIOD_M5;
input ENUM_TIMEFRAMES    SignalTF                    = PERIOD_M5;
input bool               TradeAllSessions            = true;     // Default true: Asia/London/NY/overnight
input int                ServerSessionStartHour      = 0;        // Used only when TradeAllSessions=false
input int                ServerSessionEndHour        = 23;       // Used only when TradeAllSessions=false
input bool               AllowBuy                    = true;
input bool               AllowSell                   = true;
input int                MaxSpreadPoints             = 60;
input int                SlippagePoints              = 20;

input group "Volume Profile Approximation"
input bool               UsePreviousDailyProfile     = true;
input bool               UsePreviousWeeklyProfile    = true;
input bool               UseRollingFixedProfile      = true;
input int                RollingFixedLookbackBars    = 288;      // 288 M5 bars = 24h
input int                ProfileRows                 = 96;
input double             ValueAreaPercent            = 70.0;
input int                MinProfileBars              = 30;
input bool               DrawLevelsOnChart           = true;

input group "Entry Logic"
input ENUM_ENTRY_MODEL   EntryModel                  = ENTRY_DOUBLE_WICK_PLUS_INTERNAL_BREAK;
input double             TouchBufferATR              = 0.18;     // Level touch tolerance from ATR
input int                TouchBufferMinPoints        = 20;
input int                InternalBreakBars           = 5;        // Break previous small structure
input bool               UseCloseBeyondLevel         = true;     // Rejection must close back beyond level
input int                CooldownMinutes             = 30;

input group "Trend Filter"
input ENUM_TREND_FILTER  TrendFilter                 = TREND_FILTER_OFF;
input ENUM_TIMEFRAMES    TrendTF                     = PERIOD_H1;
input int                TrendEmaPeriod              = 200;

input group "Risk / Orders"
input ENUM_RISK_MODE     RiskMode                    = RISK_PERCENT_EQUITY;
input double             FixedLot                    = 0.01;
input double             RiskPercent                 = 0.50;
input double             RewardRisk                  = 2.00;
input double             SL_ATR_Buffer               = 0.35;
input int                MinSLPoints                 = 120;
input int                MaxTradesPerDay             = 4;
input int                MaxOpenPositions            = 1;
input double             MaxDailyLossPercent         = 3.0;

input group "Management"
input bool               UseBreakEven                = true;
input double             BreakEvenAtRR               = 1.00;
input int                BreakEvenPlusPoints         = 10;
input bool               UseATRTrailing              = true;
input double             TrailStartRR                = 1.50;
input double             TrailATR                    = 1.00;
input int                ATRPeriod                   = 14;

//------------------------- STRUCTS ---------------------------------
struct ProfileLevel
{
   string   name;
   datetime fromTime;
   datetime toTime;
   double   poc;
   double   vah;
   double   val;
   bool     valid;
};

struct TradeLevel
{
   string name;
   double price;
   int    sideHint; // +1 support/buy bias if current price above, -1 resistance/sell bias if below
};

//------------------------- GLOBALS ---------------------------------
int      g_atrHandle = INVALID_HANDLE;
int      g_emaHandle = INVALID_HANDLE;
datetime g_lastSignalBar = 0;
datetime g_lastProfileUpdateBar = 0;
datetime g_lastTradeTime = 0;
int      g_dayKey = 0;
double   g_dayStartEquity = 0.0;
int      g_tradesToday = 0;

ProfileLevel g_pd;
ProfileLevel g_pw;
ProfileLevel g_fx;

//+------------------------------------------------------------------+
//| Utility                                                          |
//+------------------------------------------------------------------+
int CurrentDayKey()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

void ResetDailyCountersIfNeeded()
{
   int key = CurrentDayKey();
   if(key != g_dayKey)
   {
      g_dayKey = key;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_tradesToday = 0;
   }
}

bool IsNewBar(ENUM_TIMEFRAMES tf, datetime &lastBar)
{
   datetime t = iTime(_Symbol, tf, 0);
   if(t <= 0)
      return false;
   if(t != lastBar)
   {
      lastBar = t;
      return true;
   }
   return false;
}

double NormalizePrice(double price)
{
   return NormalizeDouble(price, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
}

double NormalizeVolumeLots(double lots)
{
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)
      step = 0.01;

   lots = MathMax(vmin, MathMin(vmax, lots));
   double steps = MathFloor((lots - vmin) / step + 1e-8);
   double out = vmin + steps * step;
   out = MathMax(vmin, MathMin(vmax, out));
   return NormalizeDouble(out, 2);
}

bool SpreadOK()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return (spread <= MaxSpreadPoints);
}

bool OptionalSessionOK()
{
   if(TradeAllSessions)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;

   int start = MathMax(0, MathMin(23, ServerSessionStartHour));
   int end   = MathMax(0, MathMin(23, ServerSessionEndHour));

   if(start == end)
      return true;

   if(start < end)
      return (h >= start && h <= end);

   // Wrapped session, e.g. 22 to 5
   return (h >= start || h <= end);
}

double GetATR(int shift=1)
{
   if(g_atrHandle == INVALID_HANDLE)
      return 0.0;

   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_atrHandle, 0, shift, 1, buf) != 1)
      return 0.0;
   return buf[0];
}

double GetEMA(int shift=1)
{
   if(g_emaHandle == INVALID_HANDLE)
      return 0.0;

   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_emaHandle, 0, shift, 1, buf) != 1)
      return 0.0;
   return buf[0];
}

int CountOpenPositionsByMagic()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      count++;
   }
   return count;
}

bool TradingLimitsOK()
{
   ResetDailyCountersIfNeeded();

   if(g_dayStartEquity <= 0.0)
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double lossLimitEquity = g_dayStartEquity * (1.0 - MaxDailyLossPercent / 100.0);
   if(MaxDailyLossPercent > 0.0 && equity <= lossLimitEquity)
      return false;

   if(MaxTradesPerDay > 0 && g_tradesToday >= MaxTradesPerDay)
      return false;

   if(MaxOpenPositions > 0 && CountOpenPositionsByMagic() >= MaxOpenPositions)
      return false;

   if(CooldownMinutes > 0 && g_lastTradeTime > 0)
   {
      if(TimeCurrent() - g_lastTradeTime < CooldownMinutes * 60)
         return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Volume profile calculation                                       |
//+------------------------------------------------------------------+
bool CalculateProfileFromRates(MqlRates &rates[], int count, string profileName, ProfileLevel &out)
{
   out.valid = false;
   out.name = profileName;
   out.poc = 0.0;
   out.vah = 0.0;
   out.val = 0.0;

   if(count < MinProfileBars)
      return false;

   int rows = MathMax(16, MathMin(300, ProfileRows));

   double lo = DBL_MAX;
   double hi = -DBL_MAX;
   for(int i = 0; i < count; ++i)
   {
      if(rates[i].low < lo)  lo = rates[i].low;
      if(rates[i].high > hi) hi = rates[i].high;
   }

   if(hi <= lo || lo == DBL_MAX)
      return false;

   double binSize = (hi - lo) / rows;
   if(binSize <= 0.0)
      return false;

   double vols[];
   ArrayResize(vols, rows);
   ArrayInitialize(vols, 0.0);

   double totalVol = 0.0;

   for(int i = 0; i < count; ++i)
   {
      double barLow = rates[i].low;
      double barHigh = rates[i].high;
      long tv = rates[i].tick_volume;
      double vol = (double)(tv > 0 ? tv : 1);

      int startBin = (int)MathFloor((barLow - lo) / binSize);
      int endBin   = (int)MathFloor((barHigh - lo) / binSize);

      if(startBin < 0) startBin = 0;
      if(endBin < 0) endBin = 0;
      if(startBin >= rows) startBin = rows - 1;
      if(endBin >= rows) endBin = rows - 1;
      if(endBin < startBin)
      {
         int tmp = startBin;
         startBin = endBin;
         endBin = tmp;
      }

      int touched = MathMax(1, endBin - startBin + 1);
      double add = vol / touched;
      for(int b = startBin; b <= endBin; ++b)
         vols[b] += add;

      totalVol += vol;
   }

   if(totalVol <= 0.0)
      return false;

   int pocIndex = 0;
   double maxVol = vols[0];
   for(int b = 1; b < rows; ++b)
   {
      if(vols[b] > maxVol)
      {
         maxVol = vols[b];
         pocIndex = b;
      }
   }

   double target = totalVol * MathMax(10.0, MathMin(95.0, ValueAreaPercent)) / 100.0;
   int lower = pocIndex;
   int upper = pocIndex;
   double accum = vols[pocIndex];

   while(accum < target && (lower > 0 || upper < rows - 1))
   {
      double downVol = (lower > 0) ? vols[lower - 1] : -1.0;
      double upVol   = (upper < rows - 1) ? vols[upper + 1] : -1.0;

      if(upVol >= downVol && upper < rows - 1)
      {
         upper++;
         accum += vols[upper];
      }
      else if(lower > 0)
      {
         lower--;
         accum += vols[lower];
      }
      else
         break;
   }

   out.fromTime = rates[0].time;
   out.toTime   = rates[count - 1].time;
   out.poc      = NormalizePrice(lo + (pocIndex + 0.5) * binSize);
   out.val      = NormalizePrice(lo + lower * binSize);
   out.vah      = NormalizePrice(lo + (upper + 1) * binSize);
   out.valid    = true;

   return true;
}

bool CalculateProfileByTime(datetime fromTime, datetime toTime, string profileName, ProfileLevel &out)
{
   out.valid = false;
   if(fromTime <= 0 || toTime <= 0 || toTime <= fromTime)
      return false;

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(_Symbol, ProfileTF, fromTime, toTime, rates);
   if(copied <= 0)
      return false;

   return CalculateProfileFromRates(rates, copied, profileName, out);
}

bool CalculateRollingProfile(string profileName, ProfileLevel &out)
{
   out.valid = false;
   int bars = MathMax(MinProfileBars, RollingFixedLookbackBars);

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(_Symbol, ProfileTF, 1, bars, rates);
   if(copied <= 0)
      return false;

   return CalculateProfileFromRates(rates, copied, profileName, out);
}

void UpdateProfiles()
{
   if(UsePreviousDailyProfile)
   {
      datetime dFrom = iTime(_Symbol, PERIOD_D1, 1);
      datetime dTo   = iTime(_Symbol, PERIOD_D1, 0);
      CalculateProfileByTime(dFrom, dTo - 1, "PD", g_pd);
   }
   else
      g_pd.valid = false;

   if(UsePreviousWeeklyProfile)
   {
      datetime wFrom = iTime(_Symbol, PERIOD_W1, 1);
      datetime wTo   = iTime(_Symbol, PERIOD_W1, 0);
      CalculateProfileByTime(wFrom, wTo - 1, "PW", g_pw);
   }
   else
      g_pw.valid = false;

   if(UseRollingFixedProfile)
      CalculateRollingProfile("FIXED", g_fx);
   else
      g_fx.valid = false;
}

void DrawOneLevel(string obj, double price, color clr, string label)
{
   if(price <= 0.0)
      return;

   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_HLINE, 0, 0, price);

   ObjectSetDouble(0, obj, OBJPROP_PRICE, price);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, obj, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, obj, OBJPROP_WIDTH, 1);
   ObjectSetString(0, obj, OBJPROP_TEXT, label);
}

void DrawProfileLevels(ProfileLevel &p)
{
   if(!DrawLevelsOnChart || !p.valid)
      return;

   string prefix = "LTA_" + p.name + "_";
   DrawOneLevel(prefix + "POC", p.poc, clrGold, p.name + " POC");
   DrawOneLevel(prefix + "VAH", p.vah, clrTomato, p.name + " VAH");
   DrawOneLevel(prefix + "VAL", p.val, clrDeepSkyBlue, p.name + " VAL");
}

void DrawAllLevels()
{
   DrawProfileLevels(g_pd);
   DrawProfileLevels(g_pw);
   DrawProfileLevels(g_fx);
}

void AddTradeLevel(TradeLevel &levels[], string name, double price, double refPrice)
{
   if(price <= 0.0)
      return;

   int n = ArraySize(levels);
   ArrayResize(levels, n + 1);
   levels[n].name = name;
   levels[n].price = price;
   levels[n].sideHint = (refPrice >= price) ? 1 : -1;
}

void BuildTradeLevels(TradeLevel &levels[])
{
   ArrayResize(levels, 0);
   double ref = iClose(_Symbol, SignalTF, 1);
   if(ref <= 0.0)
      ref = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(g_pd.valid)
   {
      AddTradeLevel(levels, "PD_POC", g_pd.poc, ref);
      AddTradeLevel(levels, "PD_VAH", g_pd.vah, ref);
      AddTradeLevel(levels, "PD_VAL", g_pd.val, ref);
   }

   if(g_pw.valid)
   {
      AddTradeLevel(levels, "PW_POC", g_pw.poc, ref);
      AddTradeLevel(levels, "PW_VAH", g_pw.vah, ref);
      AddTradeLevel(levels, "PW_VAL", g_pw.val, ref);
   }

   if(g_fx.valid)
   {
      AddTradeLevel(levels, "FIXED_POC", g_fx.poc, ref);
      AddTradeLevel(levels, "FIXED_VAH", g_fx.vah, ref);
      AddTradeLevel(levels, "FIXED_VAL", g_fx.val, ref);
   }
}

//+------------------------------------------------------------------+
//| Entry conditions                                                  |
//+------------------------------------------------------------------+
bool BullishDoubleWick(double level, double buffer)
{
   double low1 = iLow(_Symbol, SignalTF, 1);
   double low2 = iLow(_Symbol, SignalTF, 2);
   double close1 = iClose(_Symbol, SignalTF, 1);
   double close2 = iClose(_Symbol, SignalTF, 2);
   double open1 = iOpen(_Symbol, SignalTF, 1);
   double open2 = iOpen(_Symbol, SignalTF, 2);

   if(low1 <= 0.0 || low2 <= 0.0)
      return false;

   bool touchedTwice = (low1 <= level + buffer && low2 <= level + buffer);
   bool closedAbove = (!UseCloseBeyondLevel || (close1 > level && close2 > level));
   bool rejectionBody = (close1 >= open1 || close2 >= open2);

   return (touchedTwice && closedAbove && rejectionBody);
}

bool BearishDoubleWick(double level, double buffer)
{
   double high1 = iHigh(_Symbol, SignalTF, 1);
   double high2 = iHigh(_Symbol, SignalTF, 2);
   double close1 = iClose(_Symbol, SignalTF, 1);
   double close2 = iClose(_Symbol, SignalTF, 2);
   double open1 = iOpen(_Symbol, SignalTF, 1);
   double open2 = iOpen(_Symbol, SignalTF, 2);

   if(high1 <= 0.0 || high2 <= 0.0)
      return false;

   bool touchedTwice = (high1 >= level - buffer && high2 >= level - buffer);
   bool closedBelow = (!UseCloseBeyondLevel || (close1 < level && close2 < level));
   bool rejectionBody = (close1 <= open1 || close2 <= open2);

   return (touchedTwice && closedBelow && rejectionBody);
}

bool BullishInternalBreak()
{
   int bars = MathMax(2, InternalBreakBars);
   double close1 = iClose(_Symbol, SignalTF, 1);
   double hh = -DBL_MAX;
   for(int s = 2; s < 2 + bars; ++s)
   {
      double h = iHigh(_Symbol, SignalTF, s);
      if(h > hh)
         hh = h;
   }
   return (close1 > hh && hh > 0.0);
}

bool BearishInternalBreak()
{
   int bars = MathMax(2, InternalBreakBars);
   double close1 = iClose(_Symbol, SignalTF, 1);
   double ll = DBL_MAX;
   for(int s = 2; s < 2 + bars; ++s)
   {
      double l = iLow(_Symbol, SignalTF, s);
      if(l < ll)
         ll = l;
   }
   return (close1 < ll && ll < DBL_MAX);
}

bool TrendAllowsBuy()
{
   if(TrendFilter == TREND_FILTER_OFF)
      return true;

   double ema = GetEMA(1);
   double close = iClose(_Symbol, TrendTF, 1);
   if(ema <= 0.0 || close <= 0.0)
      return true; // Do not block if data unavailable

   return close >= ema;
}

bool TrendAllowsSell()
{
   if(TrendFilter == TREND_FILTER_OFF)
      return true;

   double ema = GetEMA(1);
   double close = iClose(_Symbol, TrendTF, 1);
   if(ema <= 0.0 || close <= 0.0)
      return true;

   return close <= ema;
}

bool FindSignal(int &direction, double &level, string &levelName)
{
   direction = 0;
   level = 0.0;
   levelName = "";

   TradeLevel levels[];
   BuildTradeLevels(levels);
   int n = ArraySize(levels);
   if(n <= 0)
      return false;

   double atr = GetATR(1);
   double buffer = MathMax(TouchBufferMinPoints * _Point, atr * TouchBufferATR);
   double close1 = iClose(_Symbol, SignalTF, 1);
   if(close1 <= 0.0)
      return false;

   double bestDistance = DBL_MAX;
   int bestDir = 0;
   double bestLevel = 0.0;
   string bestName = "";

   bool requireBreak = (EntryModel == ENTRY_DOUBLE_WICK_PLUS_INTERNAL_BREAK);

   for(int i = 0; i < n; ++i)
   {
      double p = levels[i].price;
      double dist = MathAbs(close1 - p);

      double lastLow = iLow(_Symbol, SignalTF, 1);
      double lastHigh = iHigh(_Symbol, SignalTF, 1);
      bool touchedOnLastBar = (lastLow <= p + buffer && lastHigh >= p - buffer);
      bool nearLevel = (dist <= buffer * 2.5 || touchedOnLastBar);
      if(!nearLevel)
         continue;

      if(AllowBuy && levels[i].sideHint >= 0 && TrendAllowsBuy())
      {
         bool dw = BullishDoubleWick(p, buffer);
         bool br = (!requireBreak || BullishInternalBreak());
         if(dw && br && dist < bestDistance)
         {
            bestDistance = dist;
            bestDir = 1;
            bestLevel = p;
            bestName = levels[i].name;
         }
      }

      if(AllowSell && levels[i].sideHint <= 0 && TrendAllowsSell())
      {
         bool dw = BearishDoubleWick(p, buffer);
         bool br = (!requireBreak || BearishInternalBreak());
         if(dw && br && dist < bestDistance)
         {
            bestDistance = dist;
            bestDir = -1;
            bestLevel = p;
            bestName = levels[i].name;
         }
      }
   }

   if(bestDir == 0)
      return false;

   direction = bestDir;
   level = bestLevel;
   levelName = bestName;
   return true;
}

//+------------------------------------------------------------------+
//| Risk and execution                                                |
//+------------------------------------------------------------------+
double CalculateLotByRisk(double entry, double sl)
{
   if(RiskMode == RISK_FIXED_LOT)
      return NormalizeVolumeLots(FixedLot);

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
   if(riskMoney <= 0.0)
      return NormalizeVolumeLots(FixedLot);

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0)
      return NormalizeVolumeLots(FixedLot);

   double stopDist = MathAbs(entry - sl);
   if(stopDist <= 0.0)
      return NormalizeVolumeLots(FixedLot);

   double moneyPerLot = (stopDist / tickSize) * tickValue;
   if(moneyPerLot <= 0.0)
      return NormalizeVolumeLots(FixedLot);

   return NormalizeVolumeLots(riskMoney / moneyPerLot);
}

void EnforceBrokerStopDistance(int direction, double entry, double &sl, double &tp)
{
   int stops = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = MathMax(MinSLPoints * _Point, stops * _Point);

   if(direction > 0)
   {
      if(entry - sl < minDist)
         sl = entry - minDist;
      if(tp - entry < minDist)
         tp = entry + minDist;
   }
   else
   {
      if(sl - entry < minDist)
         sl = entry + minDist;
      if(entry - tp < minDist)
         tp = entry - minDist;
   }

   sl = NormalizePrice(sl);
   tp = NormalizePrice(tp);
}

bool ExecuteSignal(int direction, double level, string levelName)
{
   double atr = GetATR(1);
   if(atr <= 0.0)
      atr = MathMax(100 * _Point, SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 100.0);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (direction > 0) ? ask : bid;

   double low1 = iLow(_Symbol, SignalTF, 1);
   double low2 = iLow(_Symbol, SignalTF, 2);
   double high1 = iHigh(_Symbol, SignalTF, 1);
   double high2 = iHigh(_Symbol, SignalTF, 2);

   double sl = 0.0;
   double tp = 0.0;

   if(direction > 0)
   {
      double wickLow = MathMin(low1, low2);
      sl = MathMin(wickLow, level) - SL_ATR_Buffer * atr;
      if(entry - sl < MinSLPoints * _Point)
         sl = entry - MinSLPoints * _Point;
      tp = entry + RewardRisk * (entry - sl);
   }
   else
   {
      double wickHigh = MathMax(high1, high2);
      sl = MathMax(wickHigh, level) + SL_ATR_Buffer * atr;
      if(sl - entry < MinSLPoints * _Point)
         sl = entry + MinSLPoints * _Point;
      tp = entry - RewardRisk * (sl - entry);
   }

   EnforceBrokerStopDistance(direction, entry, sl, tp);

   double lots = CalculateLotByRisk(entry, sl);
   if(lots <= 0.0)
      return false;

   string comment = StringFormat("LTA_%s_%s", (direction > 0 ? "BUY" : "SELL"), levelName);

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePoints);

   bool ok = false;
   if(direction > 0)
      ok = trade.Buy(lots, _Symbol, 0.0, sl, tp, comment);
   else
      ok = trade.Sell(lots, _Symbol, 0.0, sl, tp, comment);

   if(ok)
   {
      g_lastTradeTime = TimeCurrent();
      g_tradesToday++;
      Print("LTA EA trade opened: ", comment, " lots=", DoubleToString(lots, 2),
            " level=", DoubleToString(level, _Digits),
            " sl=", DoubleToString(sl, _Digits),
            " tp=", DoubleToString(tp, _Digits));
   }
   else
   {
      Print("LTA EA order failed. Retcode=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   }

   return ok;
}

//+------------------------------------------------------------------+
//| Position management                                               |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   double atr = GetATR(1);
   if(atr <= 0.0)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      if(sl <= 0.0 || entry <= 0.0)
         continue;

      bool isBuy = (type == POSITION_TYPE_BUY);
      double price = isBuy ? bid : ask;
      double initialRisk = isBuy ? (entry - sl) : (sl - entry);
      if(initialRisk <= 0.0)
         continue;

      double move = isBuy ? (price - entry) : (entry - price);
      double rr = move / initialRisk;

      double newSL = sl;
      bool modify = false;

      if(UseBreakEven && rr >= BreakEvenAtRR)
      {
         double beSL = isBuy ? entry + BreakEvenPlusPoints * _Point : entry - BreakEvenPlusPoints * _Point;
         beSL = NormalizePrice(beSL);

         if(isBuy && beSL > newSL)
         {
            newSL = beSL;
            modify = true;
         }
         if(!isBuy && beSL < newSL)
         {
            newSL = beSL;
            modify = true;
         }
      }

      if(UseATRTrailing && rr >= TrailStartRR)
      {
         double trailSL = isBuy ? price - TrailATR * atr : price + TrailATR * atr;
         trailSL = NormalizePrice(trailSL);

         if(isBuy && trailSL > newSL)
         {
            newSL = trailSL;
            modify = true;
         }
         if(!isBuy && trailSL < newSL)
         {
            newSL = trailSL;
            modify = true;
         }
      }

      if(modify)
      {
         if(!trade.PositionModify(ticket, newSL, tp))
            Print("PositionModify failed. Ticket=", ticket, " ret=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      }
   }
}

//+------------------------------------------------------------------+
//| Dashboard                                                         |
//+------------------------------------------------------------------+
void UpdateDashboard()
{
   string pd = g_pd.valid ? StringFormat("PD POC %.5f | VAH %.5f | VAL %.5f", g_pd.poc, g_pd.vah, g_pd.val) : "PD n/a";
   string pw = g_pw.valid ? StringFormat("PW POC %.5f | VAH %.5f | VAL %.5f", g_pw.poc, g_pw.vah, g_pw.val) : "PW n/a";
   string fx = g_fx.valid ? StringFormat("FX POC %.5f | VAH %.5f | VAL %.5f", g_fx.poc, g_fx.vah, g_fx.val) : "FIXED n/a";

   Comment(
      "LTA Concepts VP EA\n",
      "Symbol: ", _Symbol, " | SignalTF: ", EnumToString(SignalTF), " | ProfileTF: ", EnumToString(ProfileTF), "\n",
      "All Sessions: ", (TradeAllSessions ? "ON" : "OFF"), " | Spread: ", (string)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), " pts\n",
      pd, "\n",
      pw, "\n",
      fx, "\n",
      "Trades today: ", g_tradesToday, "/", MaxTradesPerDay,
      " | Open: ", CountOpenPositionsByMagic(), "/", MaxOpenPositions
   );
}

//+------------------------------------------------------------------+
//| Expert lifecycle                                                  |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePoints);

   g_atrHandle = iATR(_Symbol, SignalTF, ATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
   {
      Print("Failed to create ATR handle.");
      return INIT_FAILED;
   }

   if(TrendFilter == TREND_FILTER_EMA)
   {
      g_emaHandle = iMA(_Symbol, TrendTF, TrendEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_emaHandle == INVALID_HANDLE)
      {
         Print("Failed to create EMA handle.");
         return INIT_FAILED;
      }
   }

   g_dayKey = CurrentDayKey();
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_tradesToday = 0;

   UpdateProfiles();
   DrawAllLevels();
   UpdateDashboard();

   Print("LTA Concepts VP EA initialized on ", _Symbol, ". All sessions = ", (TradeAllSessions ? "true" : "false"));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Comment("");

   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);

   if(g_emaHandle != INVALID_HANDLE)
      IndicatorRelease(g_emaHandle);
}

void OnTick()
{
   ResetDailyCountersIfNeeded();
   ManageOpenPositions();

   datetime profileBar = g_lastProfileUpdateBar;
   if(IsNewBar(ProfileTF, profileBar))
   {
      g_lastProfileUpdateBar = profileBar;
      UpdateProfiles();
      DrawAllLevels();
   }

   if(!IsNewBar(SignalTF, g_lastSignalBar))
   {
      UpdateDashboard();
      return;
   }

   UpdateDashboard();

   if(!OptionalSessionOK())
      return;

   if(!SpreadOK())
      return;

   if(!TradingLimitsOK())
      return;

   int direction = 0;
   double level = 0.0;
   string levelName = "";

   if(FindSignal(direction, level, levelName))
      ExecuteSignal(direction, level, levelName);
}
//+------------------------------------------------------------------+

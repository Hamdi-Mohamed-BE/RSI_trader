#property strict
#property version   "1.00"
#property description "High-risk $100 to $1000 challenge EA. Uses strict sweep/displacement pending-stop entries with risk-based sizing."

#include <Trade/Trade.mqh>

CTrade Trade;

input bool            InpAllowLiveTrading       = false;
input string          InpSymbols                = "XAUUSD,US30,BTCUSD,EURUSD";
input bool            InpAutoResolveBrokerSymbols = true;
input bool            InpDebugSkips             = true;
input ENUM_TIMEFRAMES InpSignalTimeframe        = PERIOD_M5;
input ENUM_TIMEFRAMES InpTrendTimeframe         = PERIOD_H1;
input int             InpMagicNumber            = 1001000;

input double          InpRiskPercent            = 15.0;
input double          InpRewardRisk             = 4.0;
input double          InpChallengeStopBelow     = 60.0;
input double          InpChallengeTarget        = 1000.0;
input int             InpMaxTradesPerDay        = 2;
input int             InpStopAfterLossesPerDay  = 1;
input bool            InpOnePositionPerSymbol   = true;

input int             InpSwingLookbackBars      = 8;
input int             InpAtrPeriod              = 14;
input int             InpFastEmaPeriod          = 50;
input int             InpSlowEmaPeriod          = 200;
input double          InpMinBodyAtr             = 0.55;
input double          InpMinScore               = 75.0;
input double          InpEntryBufferAtr         = 0.05;
input double          InpStopBufferAtr          = 0.15;
input double          InpMaxSpreadPoints        = 0.0;
input double          InpMaxSpreadAtrPercent    = 30.0;
input int             InpPendingExpiryMinutes   = 90;

input bool            InpUseSessionFilter       = true;
input int             InpSessionOffsetHours     = 0;
input string          InpSession1Start          = "08:30";
input string          InpSession1End            = "11:30";
input string          InpSession2Start          = "14:30";
input string          InpSession2End            = "16:00";
input bool            InpTradeMonday            = true;
input bool            InpTradeTuesday           = true;
input bool            InpTradeWednesday         = true;
input bool            InpTradeThursday          = true;
input bool            InpTradeFriday            = true;

input double          InpMoveStopToBEAtR        = 1.0;
input double          InpPartialCloseAtR        = 2.0;
input double          InpPartialClosePercent    = 50.0;
input double          InpTrailStopAfterR        = 2.0;
input double          InpTrailStepR             = 1.0;
input int             InpTimerSeconds           = 10;

string   Symbols[];
datetime LastSignalBarTimes[];
string   LastSkipReasons[];
datetime LastStatusPrint = 0;

struct Signal
{
   bool   valid;
   bool   buy;
   string symbol;
   double score;
   double entry;
   double sl;
   double tp;
   double atr;
   string reason;
};

int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);

   int count = ParseSymbols(InpSymbols, Symbols);
   if(count <= 0)
   {
      Print("No symbols configured. Set InpSymbols.");
      return INIT_FAILED;
   }

   ArrayResize(LastSignalBarTimes, count);
   ArrayResize(LastSkipReasons, count);
   for(int i = 0; i < count; i++)
   {
      SymbolSelect(Symbols[i], true);
      LastSignalBarTimes[i] = 0;
      LastSkipReasons[i] = "";
   }

   EventSetTimer(MathMax(1, InpTimerSeconds));
   Print("Flip100To1000_APlusEA loaded. Live trading=", BoolText(InpAllowLiveTrading),
         ", symbols=", JoinSymbols(Symbols), ", risk=", DoubleToString(InpRiskPercent, 2),
         "%, RR=1:", DoubleToString(InpRewardRisk, 1));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   ManageOpenPositions();
}

void OnTimer()
{
   ManageOpenPositions();
   ScanSymbols();
   PrintStatus(false);
}

void ScanSymbols()
{
   if(AccountInfoDouble(ACCOUNT_BALANCE) >= InpChallengeTarget)
   {
      PrintStatus(true);
      return;
   }
   if(AccountInfoDouble(ACCOUNT_BALANCE) <= InpChallengeStopBelow)
   {
      PrintStatus(true);
      return;
   }
   if(!IsTradingDay())
      return;
   if(InpUseSessionFilter && !InSession(TimeCurrent()))
      return;

   int dayTrades = CountTodayEntryDeals();
   int losses = CountTodayConsecutiveLosses();
   if(InpMaxTradesPerDay > 0 && dayTrades >= InpMaxTradesPerDay)
      return;
   if(InpStopAfterLossesPerDay > 0 && losses >= InpStopAfterLossesPerDay)
      return;

   for(int i = 0; i < ArraySize(Symbols); i++)
   {
      string symbol = Symbols[i];
      datetime barTime = iTime(symbol, InpSignalTimeframe, 1);
      if(barTime <= 0)
      {
         DebugSkip(i, symbol, "no closed bar/history on signal timeframe");
         continue;
      }
      if(barTime == LastSignalBarTimes[i])
         continue;
      LastSignalBarTimes[i] = barTime;

      if(InpOnePositionPerSymbol && HasExposure(symbol))
      {
         DebugSkip(i, symbol, "existing position or pending order");
         continue;
      }
      string spreadReason = "";
      if(!SpreadOk(symbol, spreadReason))
      {
         DebugSkip(i, symbol, spreadReason);
         continue;
      }

      Signal signal = BuildSignal(symbol);
      if(!signal.valid)
      {
         DebugSkip(i, symbol, "no A+ setup: " + signal.reason);
         continue;
      }

      LastSkipReasons[i] = "";
      PlaceSignal(signal);
   }
}

Signal BuildSignal(const string symbol)
{
   Signal s;
   s.valid = false;
   s.symbol = symbol;
   s.reason = "";

   int needed = MathMax(InpSwingLookbackBars + 5, InpAtrPeriod + 5);
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, InpSignalTimeframe, 1, needed, rates);
   if(copied < needed - 1)
   {
      s.reason = "not enough bars";
      return s;
   }

   double atr = GetIndicatorValue(iATR(symbol, InpSignalTimeframe, InpAtrPeriod), 0, 1);
   if(atr <= 0.0)
   {
      s.reason = "atr unavailable";
      return s;
   }

   int trend = TrendDirection(symbol);
   if(trend == 0)
   {
      s.reason = "no htf trend";
      return s;
   }

   MqlRates bar = rates[0];
   double swingHigh = rates[1].high;
   double swingLow = rates[1].low;
   for(int i = 2; i <= InpSwingLookbackBars && i < copied; i++)
   {
      swingHigh = MathMax(swingHigh, rates[i].high);
      swingLow = MathMin(swingLow, rates[i].low);
   }

   double body = MathAbs(bar.close - bar.open);
   double bodyAtr = body / atr;
   if(bodyAtr < InpMinBodyAtr)
   {
      s.reason = "weak body";
      return s;
   }

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double spread = MathMax(0.0, ask - bid);
   double entryBuffer = atr * InpEntryBufferAtr;
   double stopBuffer = atr * InpStopBufferAtr;

   bool bullSweep = (bar.low < swingLow && bar.close > swingLow && bar.close > bar.open);
   bool bearSweep = (bar.high > swingHigh && bar.close < swingHigh && bar.close < bar.open);

   if(trend > 0 && bullSweep)
   {
      s.buy = true;
      s.entry = NormalizeSymbolPrice(symbol, MathMax(bar.high + entryBuffer + spread, ask + point));
      s.sl = NormalizeSymbolPrice(symbol, bar.low - stopBuffer);
      double risk = s.entry - s.sl;
      s.tp = NormalizeSymbolPrice(symbol, s.entry + risk * InpRewardRisk);
      s.score = ScoreSetup(symbol, true, bodyAtr, atr, spread);
      s.valid = ValidateTradeShape(symbol, true, s.entry, s.sl, s.tp);
      s.reason = "bull sweep + htf trend";
   }
   else if(trend < 0 && bearSweep)
   {
      s.buy = false;
      s.entry = NormalizeSymbolPrice(symbol, MathMin(bar.low - entryBuffer, bid - point));
      s.sl = NormalizeSymbolPrice(symbol, bar.high + stopBuffer + spread);
      double risk = s.sl - s.entry;
      s.tp = NormalizeSymbolPrice(symbol, s.entry - risk * InpRewardRisk);
      s.score = ScoreSetup(symbol, false, bodyAtr, atr, spread);
      s.valid = ValidateTradeShape(symbol, false, s.entry, s.sl, s.tp);
      s.reason = "bear sweep + htf trend";
   }

   if(s.valid && s.score < InpMinScore)
   {
      s.valid = false;
      s.reason = "score below A+";
   }
   return s;
}

int TrendDirection(const string symbol)
{
   double fast = GetIndicatorValue(iMA(symbol, InpTrendTimeframe, InpFastEmaPeriod, 0, MODE_EMA, PRICE_CLOSE), 0, 1);
   double slow = GetIndicatorValue(iMA(symbol, InpTrendTimeframe, InpSlowEmaPeriod, 0, MODE_EMA, PRICE_CLOSE), 0, 1);
   double close = iClose(symbol, InpTrendTimeframe, 1);
   if(fast <= 0.0 || slow <= 0.0 || close <= 0.0)
      return 0;
   if(fast > slow && close > fast)
      return 1;
   if(fast < slow && close < fast)
      return -1;
   return 0;
}

double ScoreSetup(const string symbol, const bool buy, const double bodyAtr, const double atr, const double spread)
{
   double score = 70.0;
   score += MathMin(15.0, bodyAtr * 10.0);
   double spreadPct = (atr > 0.0 ? (spread / atr) * 100.0 : 100.0);
   if(spreadPct <= 8.0)
      score += 10.0;
   else if(spreadPct <= 14.0)
      score += 5.0;
   else
      score -= 10.0;
   score += 5.0;
   return MathMax(0.0, MathMin(100.0, score));
}

bool ValidateTradeShape(const string symbol, const bool buy, const double entry, const double sl, const double tp)
{
   if(entry <= 0.0 || sl <= 0.0 || tp <= 0.0)
      return false;
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int stops = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDistance = MathMax(point, stops * point);
   double risk = buy ? entry - sl : sl - entry;
   double reward = buy ? tp - entry : entry - tp;
   if(risk <= minDistance || reward <= minDistance)
      return false;
   if(buy && !(entry > sl && tp > entry))
      return false;
   if(!buy && !(entry < sl && tp < entry))
      return false;
   return true;
}

void PlaceSignal(const Signal &signal)
{
   double volume = CalculateRiskVolume(signal.symbol, signal.entry, signal.sl);
   if(volume <= 0.0)
   {
      Print("Signal skipped ", signal.symbol, ": volume <= 0");
      return;
   }

   string side = signal.buy ? "BUY_STOP" : "SELL_STOP";
   string comment = "F1000 S" + IntegerToString((int)MathRound(signal.score)) + " RR" + DoubleToString(InpRewardRisk, 1);
   datetime expiry = TimeCurrent() + InpPendingExpiryMinutes * 60;

   Print("A+ ", signal.symbol, " ", side,
         " score=", DoubleToString(signal.score, 0),
         " lot=", DoubleToString(volume, 2),
         " entry=", DoubleToString(signal.entry, SymbolDigits(signal.symbol)),
         " sl=", DoubleToString(signal.sl, SymbolDigits(signal.symbol)),
         " tp=", DoubleToString(signal.tp, SymbolDigits(signal.symbol)),
         " reason=", signal.reason);

   if(!InpAllowLiveTrading)
   {
      Print("Live trading is disabled. Set InpAllowLiveTrading=true to place this pending order.");
      return;
   }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print("Trading is disabled in terminal or EA settings.");
      return;
   }

   Trade.SetExpertMagicNumber(InpMagicNumber);
   bool ok = false;
   if(signal.buy)
      ok = Trade.BuyStop(volume, signal.entry, signal.symbol, signal.sl, signal.tp, ORDER_TIME_SPECIFIED, expiry, comment);
   else
      ok = Trade.SellStop(volume, signal.entry, signal.symbol, signal.sl, signal.tp, ORDER_TIME_SPECIFIED, expiry, comment);

   if(!ok)
      Print("Order failed ", signal.symbol, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
}

double CalculateRiskVolume(const string symbol, const double entry, const double sl)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * MathMax(0.0, InpRiskPercent) / 100.0;
   if(riskMoney <= 0.0)
      return 0.0;

   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || step <= 0.0)
      return 0.0;

   double stopDistance = MathAbs(entry - sl);
   double riskPerLot = (stopDistance / tickSize) * tickValue;
   if(riskPerLot <= 0.0)
      return 0.0;

   double volume = riskMoney / riskPerLot;
   volume = MathFloor(volume / step) * step;
   volume = MathMax(minLot, MathMin(maxLot, volume));
   return NormalizeVolume(symbol, volume);
}

void ManageOpenPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      long type = PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double volume = PositionGetDouble(POSITION_VOLUME);
      double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_BID) : SymbolInfoDouble(symbol, SYMBOL_ASK);

      string riskKey = "F1000.initialRisk." + IntegerToString(InpMagicNumber) + "." + IntegerToString((long)ticket);
      double initialRisk = 0.0;
      if(GlobalVariableCheck(riskKey))
         initialRisk = GlobalVariableGet(riskKey);
      if(initialRisk <= 0.0)
      {
         initialRisk = MathAbs(entry - sl);
         if(initialRisk > 0.0)
            GlobalVariableSet(riskKey, initialRisk);
      }
      if(initialRisk <= 0.0)
         continue;

      double profitDistance = (type == POSITION_TYPE_BUY) ? price - entry : entry - price;
      double rNow = profitDistance / initialRisk;
      if(rNow < InpMoveStopToBEAtR)
         continue;

      double desiredSl = entry;
      if(rNow >= InpTrailStopAfterR && InpTrailStepR > 0.0)
      {
         double lockR = MathFloor(rNow / InpTrailStepR) * InpTrailStepR - InpTrailStepR;
         lockR = MathMax(0.0, lockR);
         if(type == POSITION_TYPE_BUY)
            desiredSl = entry + initialRisk * lockR;
         else
            desiredSl = entry - initialRisk * lockR;
      }
      desiredSl = NormalizeSymbolPrice(symbol, desiredSl);

      bool improve = false;
      if(type == POSITION_TYPE_BUY)
         improve = (sl <= 0.0 || desiredSl > sl) && desiredSl < price;
      else
         improve = (sl <= 0.0 || desiredSl < sl) && desiredSl > price;

      if(improve)
      {
         Trade.SetExpertMagicNumber(InpMagicNumber);
         if(!Trade.PositionModify(ticket, desiredSl, tp))
            Print("SL trail failed ticket=", ticket, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
      }

      string partialKey = "F1000.partial." + IntegerToString(InpMagicNumber) + "." + IntegerToString((long)ticket);
      if(rNow >= InpPartialCloseAtR && InpPartialClosePercent > 0.0 && !GlobalVariableCheck(partialKey))
      {
         double closeVolume = NormalizeVolume(symbol, volume * InpPartialClosePercent / 100.0);
         double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
         if(closeVolume >= minLot && closeVolume < volume)
         {
            Trade.SetExpertMagicNumber(InpMagicNumber);
            if(Trade.PositionClosePartial(ticket, closeVolume))
               GlobalVariableSet(partialKey, TimeCurrent());
            else
               Print("Partial close failed ticket=", ticket, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
         }
         else
         {
            GlobalVariableSet(partialKey, TimeCurrent());
         }
      }
   }
}

bool HasExposure(const string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == symbol)
         return true;
   }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if((int)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber && OrderGetString(ORDER_SYMBOL) == symbol)
         return true;
   }
   return false;
}

bool SpreadOk(const string symbol, string &reason)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double atr = GetIndicatorValue(iATR(symbol, InpSignalTimeframe, InpAtrPeriod), 0, 1);
   if(ask <= 0.0 || bid <= 0.0 || point <= 0.0)
   {
      reason = "no bid/ask/point data";
      return false;
   }
   double spreadPoints = (ask - bid) / point;
   if(InpMaxSpreadPoints > 0.0 && spreadPoints > InpMaxSpreadPoints)
   {
      reason = "spread points too high: " + DoubleToString(spreadPoints, 1);
      return false;
   }
   if(atr > 0.0 && InpMaxSpreadAtrPercent > 0.0)
   {
      double spreadPct = ((ask - bid) / atr) * 100.0;
      if(spreadPct > InpMaxSpreadAtrPercent)
      {
         reason = "spread/ATR too high: " + DoubleToString(spreadPct, 1) + "%";
         return false;
      }
   }
   reason = "";
   return true;
}

double GetIndicatorValue(const int handle, const int buffer, const int shift)
{
   if(handle == INVALID_HANDLE)
      return 0.0;
   double values[];
   ArraySetAsSeries(values, true);
   int copied = CopyBuffer(handle, buffer, shift, 1, values);
   IndicatorRelease(handle);
   if(copied <= 0)
      return 0.0;
   return values[0];
}

int CountTodayEntryDeals()
{
   datetime start = DayStart(TimeCurrent());
   if(!HistorySelect(start, TimeCurrent()))
      return 0;
   int count = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      if((int)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_IN)
         count++;
   }
   return count;
}

int CountTodayConsecutiveLosses()
{
   datetime start = DayStart(TimeCurrent());
   if(!HistorySelect(start, TimeCurrent()))
      return 0;

   int losses = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      if((int)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagicNumber)
         continue;
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT)
         continue;
      double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                    + HistoryDealGetDouble(deal, DEAL_SWAP)
                    + HistoryDealGetDouble(deal, DEAL_COMMISSION);
      if(profit < 0.0)
         losses++;
      else if(profit > 0.0)
         break;
   }
   return losses;
}

datetime DayStart(const datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   return StructToTime(dt);
}

bool IsTradingDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent() + InpSessionOffsetHours * 3600, dt);
   if(dt.day_of_week == 1)
      return InpTradeMonday;
   if(dt.day_of_week == 2)
      return InpTradeTuesday;
   if(dt.day_of_week == 3)
      return InpTradeWednesday;
   if(dt.day_of_week == 4)
      return InpTradeThursday;
   if(dt.day_of_week == 5)
      return InpTradeFriday;
   return false;
}

bool InSession(const datetime now)
{
   datetime shifted = now + InpSessionOffsetHours * 3600;
   MqlDateTime dt;
   TimeToStruct(shifted, dt);
   int minute = dt.hour * 60 + dt.min;
   return TimeInWindow(minute, ParseMinute(InpSession1Start), ParseMinute(InpSession1End))
       || TimeInWindow(minute, ParseMinute(InpSession2Start), ParseMinute(InpSession2End));
}

bool TimeInWindow(const int minute, const int startMinute, const int endMinute)
{
   if(startMinute < 0 || endMinute < 0)
      return false;
   if(startMinute <= endMinute)
      return minute >= startMinute && minute <= endMinute;
   return minute >= startMinute || minute <= endMinute;
}

int ParseMinute(const string value)
{
   string parts[];
   ushort separator = (ushort)StringGetCharacter(":", 0);
   if(StringSplit(value, separator, parts) != 2)
      return -1;
   int hour = (int)StringToInteger(parts[0]);
   int minute = (int)StringToInteger(parts[1]);
   if(hour < 0 || hour > 23 || minute < 0 || minute > 59)
      return -1;
   return hour * 60 + minute;
}

int ParseSymbols(const string raw, string &out[])
{
   string parts[];
   ushort separator = (ushort)StringGetCharacter(",", 0);
   int n = StringSplit(raw, separator, parts);
   ArrayResize(out, 0);
   for(int i = 0; i < n; i++)
   {
      string symbol = parts[i];
      StringTrimLeft(symbol);
      StringTrimRight(symbol);
      if(symbol == "")
         continue;
      symbol = ResolveSymbol(symbol);
      if(symbol == "")
         continue;
      if(ArrayHasSymbol(out, symbol))
         continue;
      int size = ArraySize(out);
      ArrayResize(out, size + 1);
      out[size] = symbol;
   }
   return ArraySize(out);
}

string ResolveSymbol(const string requested)
{
   string raw = requested;
   StringTrimLeft(raw);
   StringTrimRight(raw);
   if(raw == "")
      return "";

   if(SymbolSelect(raw, true))
      return raw;

   if(!InpAutoResolveBrokerSymbols)
   {
      Print("Symbol not selected/found: ", raw);
      return raw;
   }

   string best = "";
   int bestLen = 1000000;
   int total = SymbolsTotal(false);
   for(int pass = 0; pass < 2; pass++)
   {
      bool selectedOnly = (pass == 1);
      total = SymbolsTotal(selectedOnly);
      for(int i = 0; i < total; i++)
      {
         string candidate = SymbolName(i, selectedOnly);
         if(candidate == "")
            continue;
         if(StringFind(candidate, raw) != 0)
            continue;
         int len = StringLen(candidate);
         if(len < bestLen)
         {
            best = candidate;
            bestLen = len;
         }
      }
   }

   if(best != "")
   {
      SymbolSelect(best, true);
      Print("Symbol resolved: ", raw, " -> ", best);
      return best;
   }

   Print("Symbol could not be resolved: ", raw, ". Use the exact broker name from Market Watch.");
   return raw;
}

bool ArrayHasSymbol(const string &values[], const string symbol)
{
   for(int i = 0; i < ArraySize(values); i++)
   {
      if(values[i] == symbol)
         return true;
   }
   return false;
}

string JoinSymbols(const string &values[])
{
   string out = "";
   for(int i = 0; i < ArraySize(values); i++)
   {
      if(i > 0)
         out += ",";
      out += values[i];
   }
   return out;
}

void DebugSkip(const int index, const string symbol, const string reason)
{
   if(!InpDebugSkips)
      return;
   if(index < 0 || index >= ArraySize(LastSkipReasons))
   {
      Print("Skip ", symbol, ": ", reason);
      return;
   }
   if(LastSkipReasons[index] == reason)
      return;
   LastSkipReasons[index] = reason;
   Print("Skip ", symbol, ": ", reason);
}

double NormalizeSymbolPrice(const string symbol, const double price)
{
   return NormalizeDouble(price, SymbolDigits(symbol));
}

int SymbolDigits(const string symbol)
{
   return (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
}

double NormalizeVolume(const string symbol, const double volume)
{
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      return volume;
   double v = MathFloor(volume / step) * step;
   v = MathMax(minLot, MathMin(maxLot, v));
   int digits = 2;
   if(step < 0.01)
      digits = 3;
   if(step < 0.001)
      digits = 4;
   return NormalizeDouble(v, digits);
}

string BoolText(const bool value)
{
   return value ? "true" : "false";
}

void PrintStatus(const bool force)
{
   if(!force && TimeCurrent() - LastStatusPrint < 60)
      return;
   LastStatusPrint = TimeCurrent();
   Print("F1000 status balance=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
         " target=", DoubleToString(InpChallengeTarget, 2),
         " dayTrades=", CountTodayEntryDeals(), "/", InpMaxTradesPerDay,
         " lossStreak=", CountTodayConsecutiveLosses(),
         " live=", BoolText(InpAllowLiveTrading));
}

#property strict
#property version   "1.00"
#property description "ORB challenge EA: opening-range breakout with trend, ATR, spread, dynamic sizing, and trade protection."

#include <Trade/Trade.mqh>

CTrade Trade;

input bool            InpAllowLiveTrading          = false;
input string          InpSymbols                   = "XAUUSD,US30,BTCUSD,EURUSD";
input bool            InpAutoResolveBrokerSymbols  = true;
input bool            InpDebugSkips                = true;
input int             InpMagicNumber               = 1001042;

input double          InpRiskPercent               = 15.0;
input double          InpRewardRisk                = 4.0;
input double          InpChallengeStopBelow        = 60.0;
input double          InpChallengeTarget           = 1000.0;
input int             InpMaxTradesPerDay           = 2;
input int             InpStopAfterLossesPerDay     = 1;
input bool            InpOnePositionPerSymbol      = true;

input string          InpORBStartTime              = "14:30";
input int             InpSessionOffsetHours        = 0;
input int             InpOpeningRangeMinutes       = 15;
input int             InpTradeWindowMinutes        = 180;
input bool            InpCancelPendingAfterWindow  = true;
input bool            InpTradeMonday               = true;
input bool            InpTradeTuesday              = true;
input bool            InpTradeWednesday            = true;
input bool            InpTradeThursday             = true;
input bool            InpTradeFriday               = true;

input ENUM_TIMEFRAMES InpAtrTimeframe              = PERIOD_M5;
input int             InpAtrPeriod                 = 14;
input int             InpAtrExpansionLookback      = 12;
input double          InpMinAtrExpansionRatio      = 0.85;
input double          InpMinRangeAtr               = 0.40;
input double          InpMaxRangeAtr               = 2.80;
input double          InpEntryBufferAtr            = 0.05;
input double          InpStopBufferAtr             = 0.10;
input double          InpMaxSpreadRangePercent     = 18.0;
input double          InpMaxSpreadAtrPercent       = 25.0;

input ENUM_TIMEFRAMES InpTrendTimeframe1           = PERIOD_H1;
input ENUM_TIMEFRAMES InpTrendTimeframe2           = PERIOD_H4;
input int             InpFastEmaPeriod             = 50;
input int             InpSlowEmaPeriod             = 200;
input bool            InpRequireBothTrendFrames    = false;
input bool            InpPlaceBothDirections       = false;
input double          InpMinScore                  = 70.0;

input double          InpMoveStopToBEAtR           = 1.0;
input double          InpPartialCloseAtR           = 2.0;
input double          InpPartialClosePercent       = 50.0;
input double          InpTrailStartAtR             = 2.0;
input double          InpTrailAtrMultiplier        = 1.50;
input int             InpTimerSeconds              = 10;

struct ORBState
{
   datetime day_start;
   datetime range_start;
   datetime range_end;
   datetime trade_end;
   bool     orders_prepared;
   bool     range_ready;
   double   high;
   double   low;
   string   last_skip;
};

string   Symbols[];
ORBState States[];
datetime LastStatusPrint = 0;

struct ORBSignal
{
   bool     valid;
   bool     buy;
   string   symbol;
   double   score;
   double   entry;
   double   sl;
   double   tp;
   double   atr;
   double   range_size;
   string   reason;
   datetime expiry;
};

int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(25);

   int count = ParseSymbols(InpSymbols, Symbols);
   if(count <= 0)
   {
      Print("No symbols configured. Set InpSymbols.");
      return INIT_FAILED;
   }

   ArrayResize(States, count);
   for(int i = 0; i < count; i++)
   {
      SymbolSelect(Symbols[i], true);
      ResetState(i, TimeCurrent());
   }

   EventSetTimer(MathMax(1, InpTimerSeconds));
   Print("ORBChallengeEA loaded. live=", BoolText(InpAllowLiveTrading),
         ", symbols=", JoinSymbols(Symbols),
         ", risk=", DoubleToString(InpRiskPercent, 2),
         "%, RR=1:", DoubleToString(InpRewardRisk, 1),
         ", ORB start=", InpORBStartTime,
         ", range=", InpOpeningRangeMinutes, "m");
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
   ProcessORB();
   PrintStatus(false);
}

void ProcessORB()
{
   datetime now = TimeCurrent();

   if(AccountInfoDouble(ACCOUNT_BALANCE) >= InpChallengeTarget)
   {
      DeleteExpiredWindowPendings(now);
      PrintStatus(true);
      return;
   }
   if(AccountInfoDouble(ACCOUNT_BALANCE) <= InpChallengeStopBelow)
   {
      DeleteExpiredWindowPendings(now);
      PrintStatus(true);
      return;
   }
   if(!IsTradingDay(now))
   {
      DeleteExpiredWindowPendings(now);
      return;
   }

   int dayTrades = CountTodayEntryDeals();
   int lossStreak = CountTodayConsecutiveLosses();
   if(InpMaxTradesPerDay > 0 && dayTrades >= InpMaxTradesPerDay)
   {
      DeleteExpiredWindowPendings(now);
      return;
   }
   if(InpStopAfterLossesPerDay > 0 && lossStreak >= InpStopAfterLossesPerDay)
   {
      DeleteExpiredWindowPendings(now);
      return;
   }

   for(int i = 0; i < ArraySize(Symbols); i++)
   {
      string symbol = Symbols[i];
      RefreshStateForToday(i, now);

      ORBState state = States[i];
      if(now < state.range_end)
      {
         DebugSkip(i, symbol, "waiting for opening range to complete");
         continue;
      }

      if(now > state.trade_end)
      {
         DebugSkip(i, symbol, "trade window finished");
         if(InpCancelPendingAfterWindow)
            DeleteSymbolPendings(symbol);
         continue;
      }

      if(InpOnePositionPerSymbol && HasExposure(symbol))
      {
         DebugSkip(i, symbol, "existing position or pending order");
         continue;
      }

      if(state.orders_prepared)
         continue;

      if(!PrepareOpeningRange(i))
         continue;

      state = States[i];
      ORBSignal buySignal;
      ORBSignal sellSignal;
      BuildSignals(symbol, state, buySignal, sellSignal);

      bool placed = false;
      if(buySignal.valid)
      {
         PlaceSignal(buySignal);
         placed = true;
      }
      if(sellSignal.valid)
      {
         PlaceSignal(sellSignal);
         placed = true;
      }

      if(placed)
      {
         States[i].orders_prepared = true;
         States[i].last_skip = "";
      }
      else
      {
         DebugSkip(i, symbol, buySignal.reason + " | " + sellSignal.reason);
      }
   }
}

void BuildSignals(const string symbol, const ORBState &state, ORBSignal &buySignal, ORBSignal &sellSignal)
{
   InitSignal(symbol, true, state.trade_end, buySignal);
   InitSignal(symbol, false, state.trade_end, sellSignal);

   double atr = CurrentAtr(symbol);
   if(atr <= 0.0)
   {
      buySignal.reason = "ATR unavailable";
      sellSignal.reason = "ATR unavailable";
      return;
   }

   double rangeSize = state.high - state.low;
   if(rangeSize <= 0.0)
   {
      buySignal.reason = "invalid opening range";
      sellSignal.reason = "invalid opening range";
      return;
   }

   double rangeAtr = rangeSize / atr;
   if(rangeAtr < InpMinRangeAtr)
   {
      buySignal.reason = "opening range too small vs ATR";
      sellSignal.reason = "opening range too small vs ATR";
      return;
   }
   if(rangeAtr > InpMaxRangeAtr)
   {
      buySignal.reason = "opening range too large vs ATR";
      sellSignal.reason = "opening range too large vs ATR";
      return;
   }

   string spreadReason = "";
   if(!SpreadOk(symbol, rangeSize, atr, spreadReason))
   {
      buySignal.reason = spreadReason;
      sellSignal.reason = spreadReason;
      return;
   }

   if(!AtrExpansionOk(symbol))
   {
      buySignal.reason = "ATR expansion filter failed";
      sellSignal.reason = "ATR expansion filter failed";
      return;
   }

   int trend = TrendDirection(symbol);
   if(trend == 0 && !InpPlaceBothDirections)
   {
      buySignal.reason = "no higher-timeframe trend agreement";
      sellSignal.reason = "no higher-timeframe trend agreement";
      return;
   }

   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double spread = MathMax(0.0, ask - bid);
   double entryBuffer = MathMax(point, atr * InpEntryBufferAtr);
   double stopBuffer = MathMax(point, atr * InpStopBufferAtr);

   if(InpPlaceBothDirections || trend > 0)
   {
      buySignal.entry = NormalizeSymbolPrice(symbol, MathMax(state.high + entryBuffer + spread, ask + point));
      buySignal.sl = NormalizeSymbolPrice(symbol, state.low - stopBuffer);
      double risk = buySignal.entry - buySignal.sl;
      buySignal.tp = NormalizeSymbolPrice(symbol, buySignal.entry + risk * InpRewardRisk);
      buySignal.atr = atr;
      buySignal.range_size = rangeSize;
      buySignal.score = ScoreSetup(symbol, rangeAtr, atr, spread, trend > 0);
      buySignal.valid = ValidateTradeShape(symbol, true, buySignal.entry, buySignal.sl, buySignal.tp)
                      && buySignal.score >= InpMinScore;
      buySignal.reason = buySignal.valid ? "NY ORB buy breakout" : "buy score/shape failed";
   }

   if(InpPlaceBothDirections || trend < 0)
   {
      sellSignal.entry = NormalizeSymbolPrice(symbol, MathMin(state.low - entryBuffer, bid - point));
      sellSignal.sl = NormalizeSymbolPrice(symbol, state.high + stopBuffer + spread);
      double risk = sellSignal.sl - sellSignal.entry;
      sellSignal.tp = NormalizeSymbolPrice(symbol, sellSignal.entry - risk * InpRewardRisk);
      sellSignal.atr = atr;
      sellSignal.range_size = rangeSize;
      sellSignal.score = ScoreSetup(symbol, rangeAtr, atr, spread, trend < 0);
      sellSignal.valid = ValidateTradeShape(symbol, false, sellSignal.entry, sellSignal.sl, sellSignal.tp)
                       && sellSignal.score >= InpMinScore;
      sellSignal.reason = sellSignal.valid ? "NY ORB sell breakout" : "sell score/shape failed";
   }
}

void InitSignal(const string symbol, const bool buy, const datetime expiry, ORBSignal &signal)
{
   signal.valid = false;
   signal.buy = buy;
   signal.symbol = symbol;
   signal.score = 0.0;
   signal.entry = 0.0;
   signal.sl = 0.0;
   signal.tp = 0.0;
   signal.atr = 0.0;
   signal.range_size = 0.0;
   signal.reason = buy ? "buy not allowed by filters" : "sell not allowed by filters";
   signal.expiry = expiry;
}

bool PrepareOpeningRange(const int index)
{
   string symbol = Symbols[index];
   ORBState state = States[index];
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(symbol, PERIOD_M1, state.range_start, state.range_end, rates);
   if(copied <= 0)
   {
      DebugSkip(index, symbol, "no M1 data for opening range");
      return false;
   }

   double high = rates[0].high;
   double low = rates[0].low;
   for(int i = 1; i < copied; i++)
   {
      high = MathMax(high, rates[i].high);
      low = MathMin(low, rates[i].low);
   }

   if(high <= low)
   {
      DebugSkip(index, symbol, "opening range high/low invalid");
      return false;
   }

   States[index].high = high;
   States[index].low = low;
   States[index].range_ready = true;
   return true;
}

double ScoreSetup(const string symbol, const double rangeAtr, const double atr, const double spread, const bool trendAligned)
{
   double score = 55.0;
   if(rangeAtr >= 0.60 && rangeAtr <= 1.80)
      score += 18.0;
   else if(rangeAtr >= InpMinRangeAtr && rangeAtr <= InpMaxRangeAtr)
      score += 9.0;

   double spreadAtrPct = atr > 0.0 ? spread / atr * 100.0 : 100.0;
   if(spreadAtrPct <= 10.0)
      score += 12.0;
   else if(spreadAtrPct <= InpMaxSpreadAtrPercent)
      score += 6.0;

   if(trendAligned)
      score += 15.0;
   if(AtrExpansionOk(symbol))
      score += 8.0;

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

void PlaceSignal(const ORBSignal &signal)
{
   double volume = CalculateRiskVolume(signal.symbol, signal.entry, signal.sl);
   if(volume <= 0.0)
   {
      Print("ORB signal skipped ", signal.symbol, ": volume <= 0");
      return;
   }

   string side = signal.buy ? "BUY_STOP" : "SELL_STOP";
   string comment = "ORB1000 S" + IntegerToString((int)MathRound(signal.score)) + " RR" + DoubleToString(InpRewardRisk, 1);

   Print("ORB A+ ", signal.symbol, " ", side,
         " score=", DoubleToString(signal.score, 0),
         " lot=", DoubleToString(volume, 2),
         " entry=", DoubleToString(signal.entry, SymbolDigits(signal.symbol)),
         " sl=", DoubleToString(signal.sl, SymbolDigits(signal.symbol)),
         " tp=", DoubleToString(signal.tp, SymbolDigits(signal.symbol)),
         " range=", DoubleToString(signal.range_size, SymbolDigits(signal.symbol)),
         " reason=", signal.reason);

   if(!InpAllowLiveTrading)
   {
      Print("Live trading disabled. Set InpAllowLiveTrading=true to place the pending order.");
      return;
   }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print("Trading disabled in terminal or EA settings.");
      return;
   }

   Trade.SetExpertMagicNumber(InpMagicNumber);
   bool ok = false;
   if(signal.buy)
      ok = Trade.BuyStop(volume, signal.entry, signal.symbol, signal.sl, signal.tp, ORDER_TIME_SPECIFIED, signal.expiry, comment);
   else
      ok = Trade.SellStop(volume, signal.entry, signal.symbol, signal.sl, signal.tp, ORDER_TIME_SPECIFIED, signal.expiry, comment);

   if(!ok)
      Print("ORB order failed ", signal.symbol, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
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
      double price = type == POSITION_TYPE_BUY ? SymbolInfoDouble(symbol, SYMBOL_BID) : SymbolInfoDouble(symbol, SYMBOL_ASK);

      string riskKey = "ORB1000.initialRisk." + IntegerToString(InpMagicNumber) + "." + IntegerToString((long)ticket);
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

      double profitDistance = type == POSITION_TYPE_BUY ? price - entry : entry - price;
      double rNow = profitDistance / initialRisk;

      if(rNow >= InpMoveStopToBEAtR)
      {
         double desiredSl = entry;
         if(rNow >= InpTrailStartAtR)
         {
            double atr = CurrentAtr(symbol);
            if(atr > 0.0 && InpTrailAtrMultiplier > 0.0)
            {
               if(type == POSITION_TYPE_BUY)
                  desiredSl = MathMax(entry, price - atr * InpTrailAtrMultiplier);
               else
                  desiredSl = MathMin(entry, price + atr * InpTrailAtrMultiplier);
            }
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
               Print("ORB trail failed ticket=", ticket, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
         }
      }

      string partialKey = "ORB1000.partial." + IntegerToString(InpMagicNumber) + "." + IntegerToString((long)ticket);
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
               Print("ORB partial close failed ticket=", ticket, " retcode=", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
         }
         else
         {
            GlobalVariableSet(partialKey, TimeCurrent());
         }
      }
   }
}

bool SpreadOk(const string symbol, const double rangeSize, const double atr, string &reason)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
   {
      reason = "no bid/ask data";
      return false;
   }

   double spread = MathMax(0.0, ask - bid);
   if(rangeSize > 0.0 && InpMaxSpreadRangePercent > 0.0)
   {
      double pct = spread / rangeSize * 100.0;
      if(pct > InpMaxSpreadRangePercent)
      {
         reason = "spread/range too high: " + DoubleToString(pct, 1) + "%";
         return false;
      }
   }
   if(atr > 0.0 && InpMaxSpreadAtrPercent > 0.0)
   {
      double pct = spread / atr * 100.0;
      if(pct > InpMaxSpreadAtrPercent)
      {
         reason = "spread/ATR too high: " + DoubleToString(pct, 1) + "%";
         return false;
      }
   }
   reason = "";
   return true;
}

bool AtrExpansionOk(const string symbol)
{
   int handle = iATR(symbol, InpAtrTimeframe, InpAtrPeriod);
   if(handle == INVALID_HANDLE)
      return false;

   int needed = MathMax(3, InpAtrExpansionLookback + 2);
   double values[];
   ArraySetAsSeries(values, true);
   int copied = CopyBuffer(handle, 0, 1, needed, values);
   IndicatorRelease(handle);
   if(copied < 3)
      return false;

   double current = values[0];
   double sum = 0.0;
   int count = 0;
   for(int i = 1; i < copied; i++)
   {
      sum += values[i];
      count++;
   }
   if(current <= 0.0 || count <= 0)
      return false;
   double average = sum / count;
   if(average <= 0.0)
      return true;
   return current >= average * InpMinAtrExpansionRatio;
}

double CurrentAtr(const string symbol)
{
   int handle = iATR(symbol, InpAtrTimeframe, InpAtrPeriod);
   if(handle == INVALID_HANDLE)
      return 0.0;
   double values[];
   ArraySetAsSeries(values, true);
   int copied = CopyBuffer(handle, 0, 1, 1, values);
   IndicatorRelease(handle);
   if(copied <= 0)
      return 0.0;
   return values[0];
}

int TrendDirection(const string symbol)
{
   int t1 = TrendDirectionForTimeframe(symbol, InpTrendTimeframe1);
   int t2 = TrendDirectionForTimeframe(symbol, InpTrendTimeframe2);

   if(InpRequireBothTrendFrames)
   {
      if(t1 > 0 && t2 > 0)
         return 1;
      if(t1 < 0 && t2 < 0)
         return -1;
      return 0;
   }

   if(t1 == t2)
      return t1;
   if(t1 != 0 && t2 == 0)
      return t1;
   if(t2 != 0 && t1 == 0)
      return t2;
   return 0;
}

int TrendDirectionForTimeframe(const string symbol, const ENUM_TIMEFRAMES timeframe)
{
   double fast = GetIndicatorValue(iMA(symbol, timeframe, InpFastEmaPeriod, 0, MODE_EMA, PRICE_CLOSE), 0, 1);
   double slow = GetIndicatorValue(iMA(symbol, timeframe, InpSlowEmaPeriod, 0, MODE_EMA, PRICE_CLOSE), 0, 1);
   double close = iClose(symbol, timeframe, 1);
   if(fast <= 0.0 || slow <= 0.0 || close <= 0.0)
      return 0;
   if(fast > slow && close > fast)
      return 1;
   if(fast < slow && close < fast)
      return -1;
   return 0;
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

void DeleteExpiredWindowPendings(const datetime now)
{
   if(!InpCancelPendingAfterWindow)
      return;
   for(int i = 0; i < ArraySize(Symbols); i++)
   {
      RefreshStateForToday(i, now);
      if(now > States[i].trade_end)
         DeleteSymbolPendings(Symbols[i]);
   }
}

void DeleteSymbolPendings(const string symbol)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != symbol)
         continue;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP)
         continue;
      Trade.OrderDelete(ticket);
   }
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

void ResetState(const int index, const datetime now)
{
   States[index].day_start = TradingDayStart(now);
   States[index].range_start = SessionTimeToday(now, InpORBStartTime);
   States[index].range_end = States[index].range_start + MathMax(1, InpOpeningRangeMinutes) * 60;
   States[index].trade_end = States[index].range_start + MathMax(InpOpeningRangeMinutes + 1, InpTradeWindowMinutes) * 60;
   States[index].orders_prepared = false;
   States[index].range_ready = false;
   States[index].high = 0.0;
   States[index].low = 0.0;
   States[index].last_skip = "";
}

void RefreshStateForToday(const int index, const datetime now)
{
   datetime today = TradingDayStart(now);
   if(States[index].day_start != today)
      ResetState(index, now);
}

datetime TradingDayStart(const datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now + InpSessionOffsetHours * 3600, dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   return StructToTime(dt) - InpSessionOffsetHours * 3600;
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

datetime SessionTimeToday(const datetime now, const string hhmm)
{
   MqlDateTime dt;
   TimeToStruct(now + InpSessionOffsetHours * 3600, dt);
   int minuteOfDay = ParseMinute(hhmm);
   if(minuteOfDay < 0)
      minuteOfDay = 14 * 60 + 30;
   dt.hour = minuteOfDay / 60;
   dt.min = minuteOfDay % 60;
   dt.sec = 0;
   return StructToTime(dt) - InpSessionOffsetHours * 3600;
}

bool IsTradingDay(const datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now + InpSessionOffsetHours * 3600, dt);
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
   for(int pass = 0; pass < 2; pass++)
   {
      bool selectedOnly = pass == 1;
      int total = SymbolsTotal(selectedOnly);
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

void DebugSkip(const int index, const string symbol, const string reason)
{
   if(!InpDebugSkips)
      return;
   if(index < 0 || index >= ArraySize(States))
   {
      Print("ORB skip ", symbol, ": ", reason);
      return;
   }
   if(States[index].last_skip == reason)
      return;
   States[index].last_skip = reason;
   Print("ORB skip ", symbol, ": ", reason);
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
   Print("ORB1000 status balance=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
         " target=", DoubleToString(InpChallengeTarget, 2),
         " dayTrades=", CountTodayEntryDeals(), "/", InpMaxTradesPerDay,
         " lossStreak=", CountTodayConsecutiveLosses(),
         " live=", BoolText(InpAllowLiveTrading));
}

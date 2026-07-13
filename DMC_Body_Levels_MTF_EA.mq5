//+------------------------------------------------------------------+
//| DMC_Body_Levels_MTF_EA.mq5                                      |
//| MetaTrader 5 Expert Advisor                                     |
//|                                                                  |
//| Implements a practical EA version of the TradingView             |
//| "DMC Body Levels + Setups" idea:                                 |
//| - Builds candle body-edge levels from MN1/W1/D1/H4/H1.           |
//| - Classifies levels as Virgin, Tested, or Passed.                |
//| - Draws marked levels on the chart.                              |
//| - Uses M15 closed candles for GAIN/LOSE/FAIL entries.            |
//|                                                                  |
//| This is an interpretation for testing/demo use. It is not a      |
//| guaranteed profitable strategy. Backtest and forward-test first. |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "DMC body-level EA: M/W/D/H4/H1 body levels, M15 entries."

#include <Trade/Trade.mqh>

enum ENUM_DMC_STATE
{
   DMC_VIRGIN = 0,
   DMC_TESTED = 1,
   DMC_PASSED = 2
};

enum ENUM_DMC_ENTRY_MODE
{
   ENTRY_FAIL_ONLY = 0,
   ENTRY_BREAK_ONLY = 1,
   ENTRY_FAIL_AND_BREAK = 2
};

enum ENUM_DMC_TARGET_MODE
{
   TARGET_NEXT_LEVEL = 0,
   TARGET_FIXED_RR = 1
};

struct DmcLevel
{
   double price;
   int    state;
   string tags;
   int    confluence;
   color  line_color;
};

input string               InpEAName               = "DMC Body Levels MTF EA";
input ulong                InpMagicNumber          = 8787501;
input bool                 InpEnableTrading        = false;
input ENUM_TIMEFRAMES      InpEntryTimeframe       = PERIOD_M15;
input ENUM_DMC_ENTRY_MODE  InpEntryMode            = ENTRY_FAIL_AND_BREAK;
input ENUM_DMC_TARGET_MODE InpTargetMode           = TARGET_NEXT_LEVEL;
input double               InpRewardRisk           = 2.0;

input bool                 InpAllowBuy             = true;
input bool                 InpAllowSell            = true;
input bool                 InpOnePositionPerSymbol = true;
input int                  InpMaxTradesPerDay      = 3;
input int                  InpMaxSpreadPoints      = 250;
input int                  InpSlippagePoints       = 30;

input bool                 InpUseRiskPercent       = false;
input double               InpFixedLot             = 0.01;
input double               InpRiskPercent          = 1.0;
input int                  InpStopBufferPoints     = 50;

input int                  InpLookbackBarsPerTF    = 36;
input int                  InpMinConfluence        = 1;
input bool                 InpUseMN1               = true;
input bool                 InpUseW1                = true;
input bool                 InpUseD1                = true;
input bool                 InpUseH4                = true;
input bool                 InpUseH1                = true;

input bool                 InpDrawLevels           = true;
input bool                 InpShowTestedLevels     = true;
input bool                 InpShowPassedLevels     = false;
input int                  InpMaxLevelsPerSide     = 6;
input int                  InpLabelBarsRight       = 10;
input color                InpVirginColor          = clrWhite;
input color                InpTestedColor          = clrSilver;
input color                InpPassedColor          = clrDimGray;
input color                InpConfluenceColor      = clrAqua;
input color                InpFloorColor           = clrDeepSkyBlue;
input color                InpTargetColor          = clrYellow;

CTrade trade;
DmcLevel g_levels[];
datetime g_last_entry_bar = 0;
datetime g_last_draw_time = 0;
string PREFIX = "DMC_MTF_EA_";

//+------------------------------------------------------------------+
//| Utility                                                          |
//+------------------------------------------------------------------+
double TickSize()
{
   double v = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   return (v > 0.0 ? v : _Point);
}

double NormalizePrice(double price)
{
   return NormalizeDouble(price, _Digits);
}

string TFTag(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_MN1: return "M";
      case PERIOD_W1:  return "W";
      case PERIOD_D1:  return "D";
      case PERIOD_H4:  return "4H";
      case PERIOD_H1:  return "1H";
      default:         return EnumToString(tf);
   }
}

string StateText(int state)
{
   if(state == DMC_VIRGIN) return "VIRGIN";
   if(state == DMC_TESTED) return "TESTED";
   return "PASSED";
}

bool ShouldShowState(int state)
{
   if(state == DMC_VIRGIN) return true;
   if(state == DMC_TESTED) return InpShowTestedLevels;
   return InpShowPassedLevels;
}

bool SameLevel(double a, double b)
{
   return MathAbs(a - b) <= TickSize();
}

double BodyTop(MqlRates &bar)
{
   return MathMax(bar.open, bar.close);
}

double BodyBottom(MqlRates &bar)
{
   return MathMin(bar.open, bar.close);
}

//+------------------------------------------------------------------+
//| Level Engine                                                     |
//+------------------------------------------------------------------+
int ClassifyLevel(MqlRates &rates[], int idx, double level)
{
   bool touched = false;
   bool body_through = false;
   bool fully_above = false;
   bool fully_below = false;

   for(int j = 0; j < idx; j++)
   {
      if(rates[j].low <= level && level <= rates[j].high)
         touched = true;

      if(rates[j].low > level)
         fully_above = true;

      if(rates[j].high < level)
         fully_below = true;

      double bt = BodyTop(rates[j]);
      double bb = BodyBottom(rates[j]);
      if(bb < level && level < bt)
         body_through = true;
   }

   bool gap_through = fully_above && fully_below && !touched;
   bool passed = body_through || gap_through;
   if(passed) return DMC_PASSED;
   if(touched) return DMC_TESTED;
   return DMC_VIRGIN;
}

void AddLevel(double price, int state, string tag, color clr)
{
   if(price <= 0.0)
      return;

   price = NormalizePrice(price);
   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      if(SameLevel(g_levels[i].price, price))
      {
         if(StringFind(g_levels[i].tags, tag) < 0)
         {
            g_levels[i].tags += "/" + tag;
            g_levels[i].confluence++;
            g_levels[i].line_color = InpConfluenceColor;
         }
         if(state < g_levels[i].state)
            g_levels[i].state = state;
         return;
      }
   }

   ArrayResize(g_levels, n + 1);
   g_levels[n].price = price;
   g_levels[n].state = state;
   g_levels[n].tags = tag;
   g_levels[n].confluence = 1;
   g_levels[n].line_color = clr;
}

void BuildTimeframeLevels(ENUM_TIMEFRAMES tf, color clr)
{
   int count = MathMax(4, InpLookbackBarsPerTF);
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, tf, 1, count, rates);
   if(copied <= 2)
      return;

   string tag = TFTag(tf);
   for(int i = 0; i < copied; i++)
   {
      if(rates[i].open <= 0.0 || rates[i].close <= 0.0)
         continue;

      double top = BodyTop(rates[i]);
      double bot = BodyBottom(rates[i]);
      AddLevel(top, ClassifyLevel(rates, i, top), tag, clr);
      AddLevel(bot, ClassifyLevel(rates, i, bot), tag, clr);
   }
}

void BuildAllLevels()
{
   ArrayResize(g_levels, 0);
   if(InpUseMN1) BuildTimeframeLevels(PERIOD_MN1, clrOrange);
   if(InpUseW1)  BuildTimeframeLevels(PERIOD_W1,  clrMagenta);
   if(InpUseD1)  BuildTimeframeLevels(PERIOD_D1,  clrTeal);
   if(InpUseH4)  BuildTimeframeLevels(PERIOD_H4,  clrDodgerBlue);
   if(InpUseH1)  BuildTimeframeLevels(PERIOD_H1,  clrLimeGreen);
}

bool FindActivePocket(double ref_price, double &floor_level, double &target_level, string &floor_tag, string &target_tag)
{
   floor_level = 0.0;
   target_level = 0.0;
   floor_tag = "";
   target_tag = "";

   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      if(g_levels[i].state != DMC_VIRGIN)
         continue;
      if(g_levels[i].confluence < InpMinConfluence)
         continue;

      double lv = g_levels[i].price;
      if(lv < ref_price && (floor_level <= 0.0 || lv > floor_level))
      {
         floor_level = lv;
         floor_tag = g_levels[i].tags;
      }
      if(lv > ref_price && (target_level <= 0.0 || lv < target_level))
      {
         target_level = lv;
         target_tag = g_levels[i].tags;
      }
   }

   return (floor_level > 0.0 || target_level > 0.0);
}

double FindNearestVirginAbove(double ref_price)
{
   double result = 0.0;
   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      if(g_levels[i].state != DMC_VIRGIN || g_levels[i].confluence < InpMinConfluence)
         continue;
      if(g_levels[i].price > ref_price && (result <= 0.0 || g_levels[i].price < result))
         result = g_levels[i].price;
   }
   return result;
}

double FindNearestVirginBelow(double ref_price)
{
   double result = 0.0;
   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      if(g_levels[i].state != DMC_VIRGIN || g_levels[i].confluence < InpMinConfluence)
         continue;
      if(g_levels[i].price < ref_price && (result <= 0.0 || g_levels[i].price > result))
         result = g_levels[i].price;
   }
   return result;
}

//+------------------------------------------------------------------+
//| Drawing                                                          |
//+------------------------------------------------------------------+
void DeleteDmcObjects()
{
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, PREFIX) == 0)
         ObjectDelete(0, name);
   }
}

int RankFromPrice(double level, double px, bool below_side)
{
   int rank = 0;
   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      if(!ShouldShowState(g_levels[i].state) || g_levels[i].confluence < InpMinConfluence)
         continue;
      double other = g_levels[i].price;
      if(below_side && other <= px && other > level)
         rank++;
      if(!below_side && other >= px && other < level)
         rank++;
   }
   return rank;
}

void DrawAllLevels()
{
   if(!InpDrawLevels)
   {
      DeleteDmcObjects();
      return;
   }

   DeleteDmcObjects();

   double px = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double floor_level, target_level;
   string floor_tag, target_tag;
   FindActivePocket(px, floor_level, target_level, floor_tag, target_tag);

   datetime label_time = TimeCurrent() + PeriodSeconds(_Period) * InpLabelBarsRight;
   int n = ArraySize(g_levels);
   for(int i = 0; i < n; i++)
   {
      DmcLevel lv = g_levels[i];
      if(!ShouldShowState(lv.state) || lv.confluence < InpMinConfluence)
         continue;

      bool is_floor = floor_level > 0.0 && SameLevel(lv.price, floor_level);
      bool is_target = target_level > 0.0 && SameLevel(lv.price, target_level);
      bool below_side = lv.price <= px;
      int rank = RankFromPrice(lv.price, px, below_side);
      if(rank >= InpMaxLevelsPerSide && !is_floor && !is_target)
         continue;

      color draw_color = lv.line_color;
      if(lv.confluence > 1)
         draw_color = InpConfluenceColor;
      if(lv.state == DMC_TESTED)
         draw_color = InpTestedColor;
      if(lv.state == DMC_PASSED)
         draw_color = InpPassedColor;
      if(is_floor)
         draw_color = InpFloorColor;
      if(is_target)
         draw_color = InpTargetColor;

      string name = PREFIX + "LINE_" + IntegerToString(i);
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, lv.price);
      ObjectSetInteger(0, name, OBJPROP_COLOR, draw_color);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, (is_floor || is_target || lv.confluence > 1) ? 2 : 1);
      ObjectSetInteger(0, name, OBJPROP_STYLE, lv.state == DMC_VIRGIN ? STYLE_SOLID : STYLE_DOT);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);

      string label = StateText(lv.state) + " " + DoubleToString(lv.price, _Digits) + " " + lv.tags;
      if(lv.confluence > 1)
         label += " x" + IntegerToString(lv.confluence);
      if(is_floor)
         label += " LastG";
      if(is_target)
         label += " Next";

      string text_name = PREFIX + "TEXT_" + IntegerToString(i);
      ObjectCreate(0, text_name, OBJ_TEXT, 0, label_time, lv.price);
      ObjectSetString(0, text_name, OBJPROP_TEXT, label);
      ObjectSetInteger(0, text_name, OBJPROP_COLOR, draw_color);
      ObjectSetInteger(0, text_name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, text_name, OBJPROP_ANCHOR, ANCHOR_LEFT);
   }
}

//+------------------------------------------------------------------+
//| Risk / trading helpers                                           |
//+------------------------------------------------------------------+
int TodayTradeCount()
{
   datetime now = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(now, dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   datetime day_start = StructToTime(dt);
   HistorySelect(day_start, now);

   int count = 0;
   int deals = HistoryDealsTotal();
   for(int i = 0; i < deals; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      count++;
   }
   return count;
}

int OpenPositionCount()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      count++;
   }
   return count;
}

double NormalizeVolume(double volume)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      step = 0.01;

   volume = MathMax(volume, min_lot);
   volume = MathMin(volume, max_lot);
   volume = MathFloor(volume / step) * step;
   return NormalizeDouble(volume, 2);
}

double CalculateLots(double entry, double sl)
{
   if(!InpUseRiskPercent)
      return NormalizeVolume(InpFixedLot);

   double tick_size = TickSize();
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0.0 || tick_value <= 0.0)
      return NormalizeVolume(InpFixedLot);

   double risk_money = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
   double risk_per_lot = MathAbs(entry - sl) / tick_size * tick_value;
   if(risk_per_lot <= 0.0)
      return NormalizeVolume(InpFixedLot);

   return NormalizeVolume(risk_money / risk_per_lot);
}

bool SpreadOk()
{
   if(InpMaxSpreadPoints <= 0)
      return true;
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   return spread <= InpMaxSpreadPoints;
}

bool StopsOk(bool buy, double entry, double sl, double tp)
{
   int stops = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double min_dist = stops * _Point;
   if(min_dist <= 0.0)
      return true;

   if(buy)
      return (entry - sl >= min_dist && tp - entry >= min_dist);
   return (sl - entry >= min_dist && entry - tp >= min_dist);
}

bool SendMarketOrder(bool buy, double sl, double tp, string reason)
{
   if(!InpEnableTrading)
   {
      Print(InpEAName, ": signal only, trading disabled. ", reason,
            " SL=", DoubleToString(sl, _Digits), " TP=", DoubleToString(tp, _Digits));
      return false;
   }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print(InpEAName, ": trading is not allowed by terminal/EA settings.");
      return false;
   }

   if(!SpreadOk())
   {
      Print(InpEAName, ": spread blocked entry. Spread=", SymbolInfoInteger(_Symbol, SYMBOL_SPREAD));
      return false;
   }

   if(InpMaxTradesPerDay > 0 && TodayTradeCount() >= InpMaxTradesPerDay)
   {
      Print(InpEAName, ": max trades per day reached.");
      return false;
   }

   if(InpOnePositionPerSymbol && OpenPositionCount() > 0)
   {
      Print(InpEAName, ": existing EA position on symbol, skipping.");
      return false;
   }

   double entry = buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   sl = NormalizePrice(sl);
   tp = NormalizePrice(tp);
   entry = NormalizePrice(entry);

   if(!StopsOk(buy, entry, sl, tp))
   {
      Print(InpEAName, ": broker stop-distance blocked entry. entry=",
            DoubleToString(entry, _Digits), " sl=", DoubleToString(sl, _Digits),
            " tp=", DoubleToString(tp, _Digits));
      return false;
   }

   double lots = CalculateLots(entry, sl);
   trade.SetExpertMagicNumber((long)InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);

   string comment = "DMC " + reason;
   bool ok = buy
      ? trade.Buy(lots, _Symbol, 0.0, sl, tp, comment)
      : trade.Sell(lots, _Symbol, 0.0, sl, tp, comment);

   if(!ok)
   {
      Print(InpEAName, ": order failed. Retcode=", trade.ResultRetcode(),
            " ", trade.ResultRetcodeDescription());
      return false;
   }

   Print(InpEAName, ": opened ", buy ? "BUY" : "SELL",
         " lots=", DoubleToString(lots, 2),
         " reason=", reason,
         " SL=", DoubleToString(sl, _Digits),
         " TP=", DoubleToString(tp, _Digits));
   return true;
}

//+------------------------------------------------------------------+
//| Entry Engine                                                     |
//+------------------------------------------------------------------+
bool NewEntryBar()
{
   datetime t = iTime(_Symbol, InpEntryTimeframe, 0);
   if(t <= 0)
      return false;
   if(t == g_last_entry_bar)
      return false;
   g_last_entry_bar = t;
   return true;
}

double TargetForBuy(double entry, double sl)
{
   double risk = MathAbs(entry - sl);
   if(InpTargetMode == TARGET_NEXT_LEVEL)
   {
      double next = FindNearestVirginAbove(entry);
      if(next > entry)
         return NormalizePrice(next);
   }
   return NormalizePrice(entry + risk * MathMax(0.1, InpRewardRisk));
}

double TargetForSell(double entry, double sl)
{
   double risk = MathAbs(entry - sl);
   if(InpTargetMode == TARGET_NEXT_LEVEL)
   {
      double next = FindNearestVirginBelow(entry);
      if(next > 0.0 && next < entry)
         return NormalizePrice(next);
   }
   return NormalizePrice(entry - risk * MathMax(0.1, InpRewardRisk));
}

void CheckM15Entry()
{
   MqlRates bars[];
   ArraySetAsSeries(bars, true);
   if(CopyRates(_Symbol, InpEntryTimeframe, 0, 3, bars) < 3)
      return;

   MqlRates signal = bars[1];
   MqlRates prior = bars[2];
   double ref_price = prior.close;

   double floor_level, target_level;
   string floor_tag, target_tag;
   FindActivePocket(ref_price, floor_level, target_level, floor_tag, target_tag);
   if(floor_level <= 0.0 && target_level <= 0.0)
      return;

   double body_top = BodyTop(signal);
   double body_bot = BodyBottom(signal);
   double buffer = InpStopBufferPoints * _Point;

   bool gain = target_level > 0.0 && body_bot < target_level && target_level < body_top && signal.close > target_level;
   bool lose = floor_level > 0.0 && body_bot < floor_level && floor_level < body_top && signal.close < floor_level;
   bool fail_hi = target_level > 0.0 && signal.high >= target_level && body_top <= target_level && signal.close < target_level;
   bool fail_lo = floor_level > 0.0 && signal.low <= floor_level && body_bot >= floor_level && signal.close > floor_level;

   bool allow_fail = (InpEntryMode == ENTRY_FAIL_ONLY || InpEntryMode == ENTRY_FAIL_AND_BREAK);
   bool allow_break = (InpEntryMode == ENTRY_BREAK_ONLY || InpEntryMode == ENTRY_FAIL_AND_BREAK);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(InpAllowBuy && allow_fail && fail_lo)
   {
      double sl = floor_level - buffer;
      double tp = TargetForBuy(ask, sl);
      SendMarketOrder(true, sl, tp, "FAIL_LOW " + floor_tag);
      return;
   }

   if(InpAllowSell && allow_fail && fail_hi)
   {
      double sl = target_level + buffer;
      double tp = TargetForSell(bid, sl);
      SendMarketOrder(false, sl, tp, "FAIL_HIGH " + target_tag);
      return;
   }

   if(InpAllowBuy && allow_break && gain)
   {
      double sl = target_level - buffer;
      double tp = TargetForBuy(ask, sl);
      SendMarketOrder(true, sl, tp, "GAIN " + target_tag);
      return;
   }

   if(InpAllowSell && allow_break && lose)
   {
      double sl = floor_level + buffer;
      double tp = TargetForSell(bid, sl);
      SendMarketOrder(false, sl, tp, "LOSE " + floor_tag);
      return;
   }
}

//+------------------------------------------------------------------+
//| Lifecycle                                                        |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber((long)InpMagicNumber);
   BuildAllLevels();
   DrawAllLevels();
   Print(InpEAName, " initialized on ", _Symbol,
         ". Entry TF=", EnumToString(InpEntryTimeframe),
         ". Trading=", InpEnableTrading ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   DeleteDmcObjects();
   Comment("");
}

void OnTick()
{
   static datetime last_build = 0;
   datetime now = TimeCurrent();

   if(now - last_build >= 30)
   {
      BuildAllLevels();
      DrawAllLevels();
      last_build = now;
   }

   if(NewEntryBar())
   {
      BuildAllLevels();
      DrawAllLevels();
      CheckM15Entry();
   }

   double floor_level, target_level;
   string floor_tag, target_tag;
   FindActivePocket(SymbolInfoDouble(_Symbol, SYMBOL_BID), floor_level, target_level, floor_tag, target_tag);
   Comment(
      InpEAName, "\n",
      "Trading: ", InpEnableTrading ? "ON" : "OFF", " | Entry TF: ", EnumToString(InpEntryTimeframe), "\n",
      "Levels: ", ArraySize(g_levels), " | Spread: ", SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), " pts\n",
      "Last Gained: ", floor_level > 0.0 ? DoubleToString(floor_level, _Digits) + " " + floor_tag : "none", "\n",
      "Next Level: ", target_level > 0.0 ? DoubleToString(target_level, _Digits) + " " + target_tag : "none"
   );
}

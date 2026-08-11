//+------------------------------------------------------------------+
//|                                                LTA_Concepts_EA.mq5 |
//|  Chart-based MT5 implementation inspired by LTA Concepts:         |
//|  volume profile key levels, supply/demand, execution models,      |
//|  and 2/2/2 risk controls.                                         |
//+------------------------------------------------------------------+
#property strict
#property version   "1.10"
#property description "Auditable mechanical LTA implementation: profiles, supply/demand, EM1-EM4 and 2/2/2 controls."

#include <Trade/Trade.mqh>

enum ENUM_LTA_BIAS
{
   LTA_BIAS_AUTO    = 0,
   LTA_BIAS_BULLISH = 1,
   LTA_BIAS_BEARISH = -1,
   LTA_BIAS_BOTH    = 2
};

enum ENUM_LTA_ARCHETYPE
{
   LTA_ARCHETYPE_HYBRID     = 0,
   LTA_ARCHETYPE_MOMENTUM   = 1,
   LTA_ARCHETYPE_CONTRARIAN = 2
};

input group "LTA Bias And Timeframes"
input ENUM_LTA_BIAS      InpMacroBias              = LTA_BIAS_AUTO;
input ENUM_LTA_ARCHETYPE InpArchetype              = LTA_ARCHETYPE_HYBRID;
input ENUM_TIMEFRAMES    InpMacroTF                = PERIOD_D1;
input ENUM_TIMEFRAMES    InpZoneTF                 = PERIOD_H4;
input ENUM_TIMEFRAMES    InpStructureTF            = PERIOD_H1;
input ENUM_TIMEFRAMES    InpExecutionTF            = PERIOD_M15;
input ENUM_TIMEFRAMES    InpProfileTF              = PERIOD_M15;

input group "Profiles And Key Levels"
input bool               InpUsePreviousDayProfile  = true;
input bool               InpUsePreviousWeekProfile = true;
input bool               InpUseSwingProfile        = true;
input bool               InpUseSupplyDemandZones   = true;
input int                InpProfileBins            = 64;
input double             InpValueAreaPercent       = 70.0;
input int                InpSwingProfileBars       = 96;
input int                InpInternalSwingBars      = 32;
input int                InpMitigationLookbackBars = 5;
input double             InpKeyTouchBufferATR      = 0.18;

input group "Supply And Demand"
input int                InpZoneLookbackBars       = 220;
input int                InpBaseBars               = 3;
input int                InpZoneBreakLookbackBars  = 18;
input double             InpBaseMaxRangeATR        = 1.20;
input double             InpExpansionMinBodyATR    = 0.75;
input double             InpExpansionMinRangeATR   = 1.15;
input double             InpExpansionVolumeMult    = 1.05;
input int                InpZoneExpiryBars         = 160;
input bool               InpRequireZoneBreakStruct = true;

input group "Execution Models"
input bool               InpUseEM1DoubleWick       = true;
input bool               InpUseEM2InternalSwing    = true;
input bool               InpUseEM3CME              = true;
input bool               InpUseEM4Continuation     = true;
input double             InpMinConfirmWickRatio    = 0.25;
input double             InpMinConfirmVolumeMult   = 0.75;
input double             InpCMEBaseMaxATR          = 1.35;
input double             InpSLBufferATR            = 0.12;

input group "Risk And Trade Management"
input double             InpMomentumRiskPercent    = 2.0;
input double             InpContrarianRiskPercent  = 1.0;
input double             InpAbsoluteRiskCapPercent = 2.5;
input double             InpRewardRisk             = 2.0;
input int                InpMaxConsecutiveLosses   = 2;
input bool               InpMoveContrarianBEAt1R   = true;
input bool               InpMoveAllBEAt1R          = false;
input bool               InpOnePositionPerSymbol   = true;
input int                InpMaxSpreadPoints        = 35;
input int                InpSlippagePoints         = 20;
input int                InpMagicNumber            = 7262026;

input group "Session Controls - Server Time"
input bool               InpUseSessionFilter       = false;
input int                InpLondonStartHour        = 7;
input int                InpLondonEndHour          = 11;
input int                InpNYStartHour            = 13;
input int                InpNYEndHour              = 17;
input bool               InpCutFlatBeforeNYOpen    = false;
input int                InpNYOpenHour             = 13;
input int                InpDeadTradeMinutes       = 120;
input double             InpDeadTradeMaxR          = 0.20;
input bool               InpCloseLateNYDeadTrades  = false;
input int                InpLateNYHour             = 20;

input group "Direction Controls"
input bool               InpAllowLongs             = true;
input bool               InpAllowShorts            = true;

struct ProfileLevels
{
   bool     valid;
   string   name;
   datetime from_time;
   datetime to_time;
   double   high;
   double   low;
   double   poc;
   double   vah;
   double   val;
   double   hvn;
   double   lvn;
};

struct SDZone
{
   bool     valid;
   int      dir;
   string   name;
   datetime created;
   int      shift;
   double   low;
   double   high;
   double   strength;
};

struct CandidateLevel
{
   bool   valid;
   int    dir;
   string name;
   double price;
   double low;
   double high;
   bool   is_zone;
};

struct TradeSignal
{
   bool   valid;
   int    dir;
   string model;
   string level_name;
   bool   contrarian;
   double entry;
   double sl;
   double tp;
   double risk_percent;
};

CTrade m_trade;

datetime      g_last_bar_time      = 0;
datetime      g_last_trade_bar     = 0;
datetime      g_day_start          = 0;
int           g_consecutive_losses = 0;
double        g_daily_pnl          = 0.0;
bool          g_paused_today       = false;

ProfileLevels g_prev_day_profile;
ProfileLevels g_prev_week_profile;
ProfileLevels g_swing_profile;
SDZone        g_demand_zone;
SDZone        g_supply_zone;

//+------------------------------------------------------------------+
//| Initialization                                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpProfileBins < 12)
      return INIT_PARAMETERS_INCORRECT;
   if(InpRewardRisk < 1.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpBaseBars < 1 || InpZoneLookbackBars < 40)
      return INIT_PARAMETERS_INCORRECT;

   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippagePoints);
   m_trade.SetTypeFillingBySymbol(_Symbol);

   g_day_start = DayStart(TimeCurrent());
   UpdateDailyStats();
   RefreshContext();
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Main tick                                                        |
//+------------------------------------------------------------------+
void OnTick()
{
   ManageOpenPositions();

   datetime today = DayStart(TimeCurrent());
   if(today != g_day_start)
   {
      g_day_start = today;
      g_consecutive_losses = 0;
      g_daily_pnl = 0.0;
      g_paused_today = false;
   }

   datetime bar_time = iTime(_Symbol, InpExecutionTF, 0);
   if(bar_time == 0 || bar_time == g_last_bar_time)
      return;

   g_last_bar_time = bar_time;
   UpdateDailyStats();
   RefreshContext();

   if(!CanOpenNewTrade())
      return;

   TradeSignal signal;
   ResetSignal(signal);
   if(BuildSignal(signal))
      PlaceSignal(signal);
}

// Optimization score used only by the MT5 Strategy Tester.  It favors a
// profitable sample with enough trades and penalizes equity drawdown, rather
// than selecting the largest lucky dollar result.
double OnTester()
{
   double profit = TesterStatistics(STAT_PROFIT);
   double initial = TesterStatistics(STAT_INITIAL_DEPOSIT);
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double dd_pct = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double trades = TesterStatistics(STAT_TRADES);

   if(initial <= 0.0 || trades < 30.0 || pf <= 0.0)
      return -1000000.0 + profit;

   double return_pct = 100.0 * profit / initial;
   double sample_weight = MathSqrt(MathMin(trades, 100.0) / 100.0);
   double pf_weight = (pf >= 1.0 ? MathMin(pf, 3.0) : pf * 0.20);
   return return_pct * sample_weight * pf_weight / (1.0 + MathMax(dd_pct, 0.0));
}

//+------------------------------------------------------------------+
//| Context                                                          |
//+------------------------------------------------------------------+
void RefreshContext()
{
   ResetProfile(g_prev_day_profile, "PD");
   ResetProfile(g_prev_week_profile, "PW");
   ResetProfile(g_swing_profile, "SWING");
   ResetZone(g_demand_zone);
   ResetZone(g_supply_zone);

   if(InpUsePreviousDayProfile)
   {
      datetime from_d = iTime(_Symbol, PERIOD_D1, 1);
      datetime to_d   = iTime(_Symbol, PERIOD_D1, 0);
      if(from_d > 0 && to_d > from_d)
         CalculateProfileByTime("PD", InpProfileTF, from_d, to_d, g_prev_day_profile);
   }

   if(InpUsePreviousWeekProfile)
   {
      datetime from_w = iTime(_Symbol, PERIOD_W1, 1);
      datetime to_w   = iTime(_Symbol, PERIOD_W1, 0);
      if(from_w > 0 && to_w > from_w)
         CalculateProfileByTime("PW", InpProfileTF, from_w, to_w, g_prev_week_profile);
   }

   if(InpUseSwingProfile)
      CalculateProfileByBars("SWING", InpExecutionTF, 1, InpSwingProfileBars, g_swing_profile);

   if(InpUseSupplyDemandZones)
   {
      FindRecentZone(1, g_demand_zone);
      FindRecentZone(-1, g_supply_zone);
   }
}

void ResetProfile(ProfileLevels &p, const string name)
{
   p.valid = false;
   p.name = name;
   p.from_time = 0;
   p.to_time = 0;
   p.high = 0.0;
   p.low = 0.0;
   p.poc = 0.0;
   p.vah = 0.0;
   p.val = 0.0;
   p.hvn = 0.0;
   p.lvn = 0.0;
}

void ResetZone(SDZone &z)
{
   z.valid = false;
   z.dir = 0;
   z.name = "";
   z.created = 0;
   z.shift = -1;
   z.low = 0.0;
   z.high = 0.0;
   z.strength = 0.0;
}

void ResetCandidate(CandidateLevel &c)
{
   c.valid = false;
   c.dir = 0;
   c.name = "";
   c.price = 0.0;
   c.low = 0.0;
   c.high = 0.0;
   c.is_zone = false;
}

void ResetSignal(TradeSignal &s)
{
   s.valid = false;
   s.dir = 0;
   s.model = "";
   s.level_name = "";
   s.contrarian = false;
   s.entry = 0.0;
   s.sl = 0.0;
   s.tp = 0.0;
   s.risk_percent = 0.0;
}

//+------------------------------------------------------------------+
//| Volume profile                                                   |
//+------------------------------------------------------------------+
bool CalculateProfileByTime(const string name,
                            ENUM_TIMEFRAMES tf,
                            datetime from_time,
                            datetime to_time,
                            ProfileLevels &profile)
{
   MqlRates rates[];
   int copied = CopyRates(_Symbol, tf, from_time, to_time, rates);
   if(copied < 8)
      return false;

   ArraySetAsSeries(rates, true);
   return CalculateProfileFromRates(name, rates, copied, from_time, to_time, profile);
}

bool CalculateProfileByBars(const string name,
                            ENUM_TIMEFRAMES tf,
                            int start_shift,
                            int bars,
                            ProfileLevels &profile)
{
   MqlRates rates[];
   int copied = CopyRates(_Symbol, tf, start_shift, bars, rates);
   if(copied < 8)
      return false;

   ArraySetAsSeries(rates, true);
   datetime from_time = rates[copied - 1].time;
   datetime to_time = rates[0].time;
   return CalculateProfileFromRates(name, rates, copied, from_time, to_time, profile);
}

bool CalculateProfileFromRates(const string name,
                               MqlRates &rates[],
                               int count,
                               datetime from_time,
                               datetime to_time,
                               ProfileLevels &profile)
{
   ResetProfile(profile, name);

   double hi = -DBL_MAX;
   double lo = DBL_MAX;
   double total_volume = 0.0;

   for(int i = 0; i < count; i++)
   {
      if(rates[i].high > hi)
         hi = rates[i].high;
      if(rates[i].low < lo)
         lo = rates[i].low;
      total_volume += BarVolume(rates[i]);
   }

   if(hi <= lo || total_volume <= 0.0)
      return false;

   int bins = MaxInt(12, InpProfileBins);
   double step = (hi - lo) / (double)bins;
   if(step <= 0.0)
      return false;

   double volumes[];
   ArrayResize(volumes, bins);
   ArrayInitialize(volumes, 0.0);

   for(int i = 0; i < count; i++)
   {
      int first = (int)MathFloor((rates[i].low - lo) / step);
      int last  = (int)MathFloor((rates[i].high - lo) / step);
      first = ClampInt(first, 0, bins - 1);
      last = ClampInt(last, 0, bins - 1);
      if(last < first)
      {
         int tmp = first;
         first = last;
         last = tmp;
      }

      int touched_bins = MaxInt(1, last - first + 1);
      double add_volume = BarVolume(rates[i]) / (double)touched_bins;
      for(int b = first; b <= last; b++)
         volumes[b] += add_volume;
   }

   int poc_bin = 0;
   double max_vol = volumes[0];
   double min_nonzero = DBL_MAX;
   int lvn_bin = 0;

   for(int b = 0; b < bins; b++)
   {
      if(volumes[b] > max_vol)
      {
         max_vol = volumes[b];
         poc_bin = b;
      }
      if(volumes[b] > 0.0 && volumes[b] < min_nonzero)
      {
         min_nonzero = volumes[b];
         lvn_bin = b;
      }
   }

   double target = total_volume * ClampDouble(InpValueAreaPercent, 10.0, 95.0) / 100.0;
   int left = poc_bin;
   int right = poc_bin;
   double cumulative = volumes[poc_bin];

   while(cumulative < target && (left > 0 || right < bins - 1))
   {
      double left_vol = (left > 0 ? volumes[left - 1] : -1.0);
      double right_vol = (right < bins - 1 ? volumes[right + 1] : -1.0);

      if(right_vol > left_vol)
      {
         right++;
         cumulative += volumes[right];
      }
      else
      {
         left--;
         cumulative += volumes[left];
      }
   }

   profile.valid = true;
   profile.name = name;
   profile.from_time = from_time;
   profile.to_time = to_time;
   profile.high = NormalizePrice(hi);
   profile.low = NormalizePrice(lo);
   profile.poc = NormalizePrice(lo + ((double)poc_bin + 0.5) * step);
   profile.vah = NormalizePrice(lo + ((double)right + 1.0) * step);
   profile.val = NormalizePrice(lo + (double)left * step);
   profile.hvn = profile.poc;
   profile.lvn = NormalizePrice(lo + ((double)lvn_bin + 0.5) * step);
   return true;
}

//+------------------------------------------------------------------+
//| Supply and demand zones                                          |
//+------------------------------------------------------------------+
bool FindRecentZone(const int dir, SDZone &zone)
{
   ResetZone(zone);

   MqlRates rates[];
   int need = MaxInt(InpZoneLookbackBars, InpBaseBars + InpZoneBreakLookbackBars + 20);
   int copied = CopyRates(_Symbol, InpZoneTF, 0, need, rates);
   if(copied < InpBaseBars + InpZoneBreakLookbackBars + 10)
      return false;

   ArraySetAsSeries(rates, true);
   double atr = ATRFromRates(rates, copied, 14, 1);
   if(atr <= 0.0)
      atr = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 100.0;

   for(int shift = 1; shift < copied - InpBaseBars - InpZoneBreakLookbackBars - 2; shift++)
   {
      if(shift > InpZoneExpiryBars)
         break;

      MqlRates expansion = rates[shift];
      double body = MathAbs(expansion.close - expansion.open);
      double range = expansion.high - expansion.low;
      double avg_vol = AverageVolume(rates, copied, shift + 1, 20);
      if(avg_vol <= 0.0)
         avg_vol = BarVolume(expansion);

      bool bullish_expansion = (expansion.close > expansion.open &&
                                body >= atr * InpExpansionMinBodyATR &&
                                range >= atr * InpExpansionMinRangeATR &&
                                BarVolume(expansion) >= avg_vol * InpExpansionVolumeMult);

      bool bearish_expansion = (expansion.close < expansion.open &&
                                body >= atr * InpExpansionMinBodyATR &&
                                range >= atr * InpExpansionMinRangeATR &&
                                BarVolume(expansion) >= avg_vol * InpExpansionVolumeMult);

      if((dir > 0 && !bullish_expansion) || (dir < 0 && !bearish_expansion))
         continue;

      double base_high = -DBL_MAX;
      double base_low = DBL_MAX;
      for(int j = shift + 1; j <= shift + InpBaseBars; j++)
      {
         base_high = MathMax(base_high, rates[j].high);
         base_low = MathMin(base_low, rates[j].low);
      }

      if(base_high <= base_low)
         continue;

      double base_range = base_high - base_low;
      if(base_range > atr * InpBaseMaxRangeATR)
         continue;

      double prior_high = HighestHigh(rates, copied, shift + InpBaseBars + 1, InpZoneBreakLookbackBars);
      double prior_low = LowestLow(rates, copied, shift + InpBaseBars + 1, InpZoneBreakLookbackBars);

      bool breaks_structure = false;
      if(dir > 0)
         breaks_structure = (expansion.close > prior_high || expansion.high > prior_high);
      else
         breaks_structure = (expansion.close < prior_low || expansion.low < prior_low);

      // In the book a meaningful zone is the base immediately before an
      // imbalance that removes opposing structure.  Do not silently accept
      // an ordinary expansion candle when this rule is enabled.
      if(InpRequireZoneBreakStruct && !breaks_structure)
         continue;

      double strength = 1.0;
      if(breaks_structure)
         strength += 1.0;
      if(BarVolume(expansion) > avg_vol * (InpExpansionVolumeMult + 0.35))
         strength += 0.5;
      if(range > atr * (InpExpansionMinRangeATR + 0.65))
         strength += 0.5;

      zone.valid = true;
      zone.dir = dir;
      zone.name = (dir > 0 ? "Demand" : "Supply");
      zone.created = expansion.time;
      zone.shift = shift;
      zone.low = NormalizePrice(base_low);
      zone.high = NormalizePrice(base_high);
      zone.strength = strength;
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Signal generation                                                |
//+------------------------------------------------------------------+
bool BuildSignal(TradeSignal &signal)
{
   ResetSignal(signal);

   int macro = GetMacroBias();
   int trend = GetTrendDirection(InpStructureTF);

   int directions[2] = { 1, -1 };
   for(int d = 0; d < 2; d++)
   {
      int dir = directions[d];
      if(dir > 0 && !InpAllowLongs)
         continue;
      if(dir < 0 && !InpAllowShorts)
         continue;
      if(!DirectionAllowedByBias(dir, macro))
         continue;

      bool contrarian = (trend != 0 && trend != dir);
      if(InpArchetype == LTA_ARCHETYPE_MOMENTUM && contrarian)
         continue;
      if(InpArchetype == LTA_ARCHETYPE_CONTRARIAN && !contrarian)
         continue;

      CandidateLevel candidate;
      ResetCandidate(candidate);
      if(!FindCandidateLevel(dir, candidate))
         continue;

      string model = "";
      double sl = 0.0;

      if(InpUseEM3CME && EntryModel3CME(dir, candidate, sl))
         model = "EM3-CME";
      else if(InpUseEM2InternalSwing && EntryModel2InternalSwing(dir, candidate, sl))
         model = "EM2-SwingProfile";
      else if(InpUseEM1DoubleWick && EntryModel1DoubleWick(dir, candidate, sl))
         model = "EM1-DoubleWick";
      else if(InpUseEM4Continuation && EntryModel4Continuation(dir, candidate, sl))
         model = "EM4-Continuation";

      if(model == "")
         continue;

      double entry = (dir > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                              : SymbolInfoDouble(_Symbol, SYMBOL_BID));
      if(entry <= 0.0)
         continue;

      double atr = GetATRValue(InpExecutionTF, 14, 1);
      double buffer = MathMax(atr * InpSLBufferATR, SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 2.0);

      if(dir > 0)
      {
         if(candidate.is_zone)
            sl = MathMin(sl, candidate.low - buffer);
         if(sl >= entry)
            sl = entry - MathMax(atr, MinimumStopDistance());
      }
      else
      {
         if(candidate.is_zone)
            sl = MathMax(sl, candidate.high + buffer);
         if(sl <= entry)
            sl = entry + MathMax(atr, MinimumStopDistance());
      }

      sl = NormalizePrice(sl);
      if(!StopDistanceValid(dir, entry, sl))
         continue;

      double risk_distance = MathAbs(entry - sl);
      double tp = (dir > 0 ? entry + risk_distance * InpRewardRisk
                           : entry - risk_distance * InpRewardRisk);
      tp = NormalizePrice(tp);

      if(MathAbs(tp - entry) < MinimumStopDistance())
         continue;

      signal.valid = true;
      signal.dir = dir;
      signal.model = model;
      signal.level_name = candidate.name;
      signal.contrarian = contrarian;
      signal.entry = NormalizePrice(entry);
      signal.sl = sl;
      signal.tp = tp;
      signal.risk_percent = (contrarian ? InpContrarianRiskPercent : InpMomentumRiskPercent);
      return true;
   }

   return false;
}

bool FindCandidateLevel(const int dir, CandidateLevel &candidate)
{
   ResetCandidate(candidate);

   double buffer = GetATRValue(InpExecutionTF, 14, 1) * InpKeyTouchBufferATR;
   if(buffer <= 0.0)
      buffer = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 20.0;

   if(InpUseSupplyDemandZones)
   {
      SDZone z;
      ResetZone(z);
      if(dir > 0)
         z = g_demand_zone;
      else
         z = g_supply_zone;
      if(z.valid && ZoneWasMitigated(dir, z, buffer))
      {
         candidate.valid = true;
         candidate.dir = dir;
         candidate.name = z.name + "(" + EnumToString(InpZoneTF) + ")";
         candidate.low = z.low;
         candidate.high = z.high;
         candidate.price = NormalizePrice((z.low + z.high) * 0.5);
         candidate.is_zone = true;
         return true;
      }
   }

   if(InpUsePreviousWeekProfile && FindProfileLevel(dir, g_prev_week_profile, "PW", buffer, candidate))
      return true;
   if(InpUsePreviousDayProfile && FindProfileLevel(dir, g_prev_day_profile, "PD", buffer, candidate))
      return true;
   if(InpUseSwingProfile && FindProfileLevel(dir, g_swing_profile, "SWING", buffer, candidate))
      return true;

   return false;
}

bool FindProfileLevel(const int dir,
                      const ProfileLevels &p,
                      const string prefix,
                      const double buffer,
                      CandidateLevel &candidate)
{
   if(!p.valid)
      return false;

   double levels[3];
   string names[3];
   levels[0] = p.poc;
   levels[1] = p.vah;
   levels[2] = p.val;
   names[0] = prefix + "-POC";
   names[1] = prefix + "-VAH";
   names[2] = prefix + "-VAL";

   double best_distance = DBL_MAX;
   int best = -1;
   double close1 = iClose(_Symbol, InpExecutionTF, 1);

   for(int i = 0; i < 3; i++)
   {
      if(levels[i] <= 0.0)
         continue;

      if(!LevelWasMitigated(dir, levels[i], buffer, InpMitigationLookbackBars))
         continue;

      if(dir > 0 && close1 < levels[i] - buffer)
         continue;
      if(dir < 0 && close1 > levels[i] + buffer)
         continue;

      double dist = MathAbs(close1 - levels[i]);
      if(dist < best_distance)
      {
         best_distance = dist;
         best = i;
      }
   }

   if(best < 0)
      return false;

   candidate.valid = true;
   candidate.dir = dir;
   candidate.name = names[best];
   candidate.price = NormalizePrice(levels[best]);
   candidate.low = NormalizePrice(levels[best] - buffer);
   candidate.high = NormalizePrice(levels[best] + buffer);
   candidate.is_zone = false;
   return true;
}

//+------------------------------------------------------------------+
//| Entry models                                                     |
//+------------------------------------------------------------------+
bool EntryModel1DoubleWick(const int dir, const CandidateLevel &level, double &sl)
{
   MqlRates r[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 0, 30, r);
   if(copied < 25)
      return false;

   ArraySetAsSeries(r, true);
   if(!ConfirmVolumeOK(r, copied, 1))
      return false;

   MqlRates a = r[1];
   MqlRates b = r[2];

   bool touch_a = BarTouchesCandidate(dir, a, level);
   bool touch_b = BarTouchesCandidate(dir, b, level);
   if(!(touch_a || touch_b))
      return false;

   double range_a = MathMax(a.high - a.low, _Point);
   double range_b = MathMax(b.high - b.low, _Point);

   if(dir > 0)
   {
      double wick_a = MathMin(a.open, a.close) - a.low;
      double wick_b = MathMin(b.open, b.close) - b.low;
      bool wick_confirm = (wick_a >= range_a * InpMinConfirmWickRatio ||
                           wick_b >= range_b * InpMinConfirmWickRatio);
      bool flip = (a.close > a.open && a.close > b.close);
      if(!wick_confirm || !flip)
         return false;
      sl = NormalizePrice(MathMin(a.low, b.low) - GetSLBuffer());
      return true;
   }

   double wick_a = a.high - MathMax(a.open, a.close);
   double wick_b = b.high - MathMax(b.open, b.close);
   bool wick_confirm = (wick_a >= range_a * InpMinConfirmWickRatio ||
                        wick_b >= range_b * InpMinConfirmWickRatio);
   bool flip = (a.close < a.open && a.close < b.close);
   if(!wick_confirm || !flip)
      return false;

   sl = NormalizePrice(MathMax(a.high, b.high) + GetSLBuffer());
   return true;
}

bool EntryModel2InternalSwing(const int dir, const CandidateLevel &level, double &sl)
{
   if(!LevelWasMitigated(dir, level.price, GetATRValue(InpExecutionTF, 14, 1) * InpKeyTouchBufferATR,
                         InpMitigationLookbackBars + InpInternalSwingBars))
      return false;

   ProfileLevels internal_profile;
   if(!CalculateProfileByBars("LTF", InpExecutionTF, 1, InpInternalSwingBars, internal_profile))
      return false;

   CandidateLevel internal_level;
   ResetCandidate(internal_level);

   double buffer = GetATRValue(InpExecutionTF, 14, 1) * InpKeyTouchBufferATR;
   if(buffer <= 0.0)
      buffer = _Point * 20.0;

   if(!FindProfileLevel(dir, internal_profile, "LTF", buffer, internal_level))
      return false;

   MqlRates r[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 0, 30, r);
   if(copied < 25)
      return false;

   ArraySetAsSeries(r, true);
   if(!ConfirmVolumeOK(r, copied, 1))
      return false;

   MqlRates a = r[1];
   MqlRates b = r[2];

   if(dir > 0)
   {
      bool reclaimed = (a.close > internal_level.price && a.close > b.high);
      bool flipped = (a.close > a.open);
      if(!(reclaimed && flipped))
         return false;
      sl = NormalizePrice(MathMin(a.low, b.low) - GetSLBuffer());
      return true;
   }

   bool reclaimed = (a.close < internal_level.price && a.close < b.low);
   bool flipped = (a.close < a.open);
   if(!(reclaimed && flipped))
      return false;

   sl = NormalizePrice(MathMax(a.high, b.high) + GetSLBuffer());
   return true;
}

bool EntryModel3CME(const int dir, const CandidateLevel &level, double &sl)
{
   int base_bars = MaxInt(3, InpBaseBars);
   MqlRates r[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 0, MaxInt(base_bars + 6, 30), r);
   if(copied < MaxInt(base_bars + 4, 25))
      return false;

   ArraySetAsSeries(r, true);

   MqlRates expansion = r[1];
   MqlRates manipulation = r[2];

   double base_high = -DBL_MAX;
   double base_low = DBL_MAX;
   for(int i = 3; i < 3 + base_bars; i++)
   {
      base_high = MathMax(base_high, r[i].high);
      base_low = MathMin(base_low, r[i].low);
   }

   double atr = GetATRValue(InpExecutionTF, 14, 1);
   if(atr <= 0.0)
      atr = _Point * 100.0;

   if((base_high - base_low) > atr * InpCMEBaseMaxATR)
      return false;

   if(!BarTouchesCandidate(dir, manipulation, level))
      return false;

   if(!ConfirmVolumeOK(r, copied, 1))
      return false;

   if(dir > 0)
   {
      bool sweep = (manipulation.low < base_low && manipulation.close > base_low);
      bool expand = (expansion.close > base_high &&
                     expansion.close > expansion.open &&
                     (expansion.high - expansion.low) >= atr * 0.75);
      if(!(sweep && expand))
         return false;
      sl = NormalizePrice(manipulation.low - GetSLBuffer());
      return true;
   }

   bool sweep = (manipulation.high > base_high && manipulation.close < base_high);
   bool expand = (expansion.close < base_low &&
                  expansion.close < expansion.open &&
                  (expansion.high - expansion.low) >= atr * 0.75);
   if(!(sweep && expand))
      return false;

   sl = NormalizePrice(manipulation.high + GetSLBuffer());
   return true;
}

bool EntryModel4Continuation(const int dir, const CandidateLevel &level, double &sl)
{
   MqlRates r[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 0, 30, r);
   if(copied < 25)
      return false;

   ArraySetAsSeries(r, true);
   if(!ConfirmVolumeOK(r, copied, 1))
      return false;

   MqlRates first = r[3];
   MqlRates second = r[2];
   MqlRates third = r[1];

   if(!(BarTouchesCandidate(dir, first, level) || BarTouchesCandidate(dir, second, level)))
      return false;

   if(dir > 0)
   {
      bool candle_flip = (second.close < second.open || second.low < first.low);
      bool confirmation = (third.close > third.open &&
                           third.close > MathMax(first.high, second.high));
      if(!(candle_flip && confirmation))
         return false;
      sl = NormalizePrice(MathMin(MathMin(first.low, second.low), third.low) - GetSLBuffer());
      return true;
   }

   bool candle_flip = (second.close > second.open || second.high > first.high);
   bool confirmation = (third.close < third.open &&
                        third.close < MathMin(first.low, second.low));
   if(!(candle_flip && confirmation))
      return false;

   sl = NormalizePrice(MathMax(MathMax(first.high, second.high), third.high) + GetSLBuffer());
   return true;
}

//+------------------------------------------------------------------+
//| Order placement and management                                   |
//+------------------------------------------------------------------+
bool PlaceSignal(const TradeSignal &signal)
{
   if(!signal.valid)
      return false;

   if(g_last_trade_bar == g_last_bar_time)
      return false;

   double volume = CalculateRiskVolume(signal.dir, signal.entry, signal.sl, signal.risk_percent);
   if(volume <= 0.0)
      return false;

   string side = (signal.dir > 0 ? "BUY" : "SELL");
   string mode = (signal.contrarian ? "CONTRA" : "MOM");
   string comment = "LTA " + signal.model + " " + signal.level_name + " " + mode;

   bool ok = false;
   if(signal.dir > 0)
      ok = m_trade.Buy(volume, _Symbol, 0.0, signal.sl, signal.tp, comment);
   else
      ok = m_trade.Sell(volume, _Symbol, 0.0, signal.sl, signal.tp, comment);

   if(ok)
      g_last_trade_bar = g_last_bar_time;

   return ok;
}

void ManageOpenPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(symbol != _Symbol || magic != InpMagicNumber)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      int dir = (type == POSITION_TYPE_BUY ? 1 : -1);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double current = (dir > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK));

      if(open_price <= 0.0 || sl <= 0.0 || current <= 0.0)
         continue;

      string comment = PositionGetString(POSITION_COMMENT);
      bool contrarian = (StringFind(comment, "CONTRA") >= 0);

      double initial_r = MathAbs(open_price - sl);
      if(initial_r <= 0.0)
         continue;

      double profit_r = (dir > 0 ? (current - open_price) / initial_r
                                 : (open_price - current) / initial_r);

      bool sl_at_breakeven = (dir > 0 ? sl >= open_price : sl <= open_price);
      bool should_be = (InpMoveAllBEAt1R || (InpMoveContrarianBEAt1R && contrarian));
      if(should_be && !sl_at_breakeven && profit_r >= 1.0)
      {
         double be = NormalizePrice(open_price);
         m_trade.PositionModify(ticket, be, tp);
      }

      if(ShouldTimeExit(ticket, dir, open_price, sl, current))
         m_trade.PositionClose(ticket);
   }
}

bool ShouldTimeExit(const ulong ticket,
                    const int dir,
                    const double open_price,
                    const double sl,
                    const double current_price)
{
   datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
   int age_minutes = (int)((TimeCurrent() - open_time) / 60);
   if(age_minutes < InpDeadTradeMinutes)
      return false;

   double initial_r = MathAbs(open_price - sl);
   if(initial_r <= 0.0)
      return false;

   double profit_r = (dir > 0 ? (current_price - open_price) / initial_r
                              : (open_price - current_price) / initial_r);
   if(profit_r > InpDeadTradeMaxR)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpCutFlatBeforeNYOpen && dt.hour == InpNYOpenHour)
      return true;

   if(InpCloseLateNYDeadTrades && dt.hour >= InpLateNYHour)
      return true;

   return false;
}

//+------------------------------------------------------------------+
//| Filters                                                          |
//+------------------------------------------------------------------+
bool CanOpenNewTrade()
{
   if(g_paused_today)
      return false;
   if(!SpreadOK())
      return false;
   if(!SessionOK())
      return false;
   if(InpOnePositionPerSymbol && CountOpenPositions() > 0)
      return false;
   if(g_last_trade_bar == g_last_bar_time)
      return false;
   return true;
}

bool SpreadOK()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread <= 0)
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      spread = (long)MathRound((ask - bid) / _Point);
   }
   return (spread <= InpMaxSpreadPoints);
}

bool SessionOK()
{
   if(!InpUseSessionFilter)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool london = HourInSession(dt.hour, InpLondonStartHour, InpLondonEndHour);
   bool ny = HourInSession(dt.hour, InpNYStartHour, InpNYEndHour);
   return (london || ny);
}

bool HourInSession(const int hour, const int start_hour, const int end_hour)
{
   if(start_hour == end_hour)
      return true;
   if(start_hour < end_hour)
      return (hour >= start_hour && hour < end_hour);
   return (hour >= start_hour || hour < end_hour);
}

int CountOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         count++;
   }
   return count;
}

int GetMacroBias()
{
   if(InpMacroBias == LTA_BIAS_BULLISH)
      return 1;
   if(InpMacroBias == LTA_BIAS_BEARISH)
      return -1;
   if(InpMacroBias == LTA_BIAS_BOTH)
      return 0;

   int macro_trend = GetTrendDirection(InpMacroTF);
   if(macro_trend != 0)
      return macro_trend;
   return GetTrendDirection(InpStructureTF);
}

bool DirectionAllowedByBias(const int dir, const int bias)
{
   if(InpMacroBias == LTA_BIAS_BOTH)
      return true;
   if(bias == 0)
      return true;
   return (dir == bias);
}

int GetTrendDirection(ENUM_TIMEFRAMES tf)
{
   MqlRates rates[];
   int copied = CopyRates(_Symbol, tf, 1, 80, rates);
   if(copied < 55)
      return 0;

   ArraySetAsSeries(rates, true);
   double fast = AverageClose(rates, copied, 0, 20);
   double slow = AverageClose(rates, copied, 0, 50);
   double close1 = rates[0].close;
   double high_recent = HighestHigh(rates, copied, 0, 10);
   double high_prior = HighestHigh(rates, copied, 10, 20);
   double low_recent = LowestLow(rates, copied, 0, 10);
   double low_prior = LowestLow(rates, copied, 10, 20);

   if(close1 > fast && fast > slow && high_recent >= high_prior)
      return 1;
   if(close1 < fast && fast < slow && low_recent <= low_prior)
      return -1;

   if(fast > slow)
      return 1;
   if(fast < slow)
      return -1;
   return 0;
}

bool ConfirmVolumeOK(MqlRates &rates[], const int count, const int shift)
{
   if(count < shift + 25)
      return true;
   double avg = AverageVolume(rates, count, shift + 1, 20);
   if(avg <= 0.0)
      return true;
   return (BarVolume(rates[shift]) >= avg * InpMinConfirmVolumeMult);
}

//+------------------------------------------------------------------+
//| Touch and mitigation logic                                       |
//+------------------------------------------------------------------+
bool BarTouchesCandidate(const int dir, const MqlRates &bar, const CandidateLevel &level)
{
   if(!level.valid)
      return false;

   if(level.is_zone)
   {
      if(dir > 0)
         return (bar.low <= level.high && bar.high >= level.low);
      return (bar.high >= level.low && bar.low <= level.high);
   }

   return (bar.low <= level.high && bar.high >= level.low);
}

bool LevelWasMitigated(const int dir, const double price, const double buffer, const int lookback)
{
   MqlRates rates[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 1, MaxInt(lookback, 1), rates);
   if(copied <= 0)
      return false;

   ArraySetAsSeries(rates, true);
   for(int i = 0; i < copied; i++)
   {
      if(rates[i].low <= price + buffer && rates[i].high >= price - buffer)
      {
         if(dir > 0 && rates[i].close >= price - buffer)
            return true;
         if(dir < 0 && rates[i].close <= price + buffer)
            return true;
      }
   }
   return false;
}

bool ZoneWasMitigated(const int dir, const SDZone &zone, const double buffer)
{
   if(!zone.valid)
      return false;

   MqlRates rates[];
   int copied = CopyRates(_Symbol, InpExecutionTF, 1, MaxInt(InpMitigationLookbackBars, 1), rates);
   if(copied <= 0)
      return false;

   ArraySetAsSeries(rates, true);
   for(int i = 0; i < copied; i++)
   {
      bool touched = (rates[i].low <= zone.high + buffer && rates[i].high >= zone.low - buffer);
      if(!touched)
         continue;

      if(dir > 0 && rates[i].close > zone.low)
         return true;
      if(dir < 0 && rates[i].close < zone.high)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Risk                                                            |
//+------------------------------------------------------------------+
double CalculateRiskVolume(const int dir,
                           const double entry,
                           const double sl,
                           const double risk_percent)
{
   double cap = ClampDouble(InpAbsoluteRiskCapPercent, 0.01, 2.5);
   double risk_pct = ClampDouble(risk_percent, 0.01, cap);
   double risk_money = AccountInfoDouble(ACCOUNT_EQUITY) * risk_pct / 100.0;
   if(risk_money <= 0.0)
      return 0.0;

   ENUM_ORDER_TYPE order_type = (dir > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double loss_for_one_lot = 0.0;
   if(!OrderCalcProfit(order_type, _Symbol, 1.0, entry, sl, loss_for_one_lot))
      return 0.0;

   loss_for_one_lot = MathAbs(loss_for_one_lot);
   if(loss_for_one_lot <= 0.0)
      return 0.0;

   double lots = risk_money / loss_for_one_lot;
   return NormalizeVolume(lots);
}

double NormalizeVolume(const double volume)
{
   double min_vol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_vol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      step = 0.01;

   // Never force the broker minimum lot when it would exceed the requested
   // monetary risk.  Skipping the trade is the only honest risk-safe choice.
   if(volume < min_vol)
      return 0.0;

   double v = MathFloor(volume / step + 1e-9) * step;
   v = MathMin(max_vol, v);

   int digits = 2;
   if(step < 0.01)
      digits = 3;
   if(step < 0.001)
      digits = 4;

   return NormalizeDouble(v, digits);
}

bool StopDistanceValid(const int dir, const double price, const double stop)
{
   double min_distance = MinimumStopDistance();
   if(min_distance <= 0.0)
      min_distance = _Point;

   if(dir > 0)
      return ((price - stop) >= min_distance);
   return ((stop - price) >= min_distance);
}

double MinimumStopDistance()
{
   long stops = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   long points = (stops > freeze ? stops : freeze);
   return (double)(points + 2) * _Point;
}

double GetSLBuffer()
{
   double atr = GetATRValue(InpExecutionTF, 14, 1);
   if(atr <= 0.0)
      atr = _Point * 50.0;
   return MathMax(atr * InpSLBufferATR, MinimumStopDistance());
}

//+------------------------------------------------------------------+
//| Daily loss control                                               |
//+------------------------------------------------------------------+
void UpdateDailyStats()
{
   g_daily_pnl = 0.0;
   g_consecutive_losses = 0;

   datetime from_time = g_day_start;
   datetime to_time = TimeCurrent();
   if(!HistorySelect(from_time, to_time))
      return;

   int total = HistoryDealsTotal();
   bool counting_losses = true;

   for(int i = total - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;

      if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol)
         continue;
      if((int)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_OUT)
         continue;

      double pnl = HistoryDealGetDouble(deal, DEAL_PROFIT) +
                   HistoryDealGetDouble(deal, DEAL_SWAP) +
                   HistoryDealGetDouble(deal, DEAL_COMMISSION);
      g_daily_pnl += pnl;

      if(counting_losses)
      {
         if(pnl < 0.0)
            g_consecutive_losses++;
         else if(pnl > 0.0)
            counting_losses = false;
      }
   }

   if(g_consecutive_losses >= InpMaxConsecutiveLosses)
   {
      if(g_daily_pnl <= 0.0)
         g_paused_today = true;
   }
}

datetime DayStart(const datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
//| Numeric helpers                                                  |
//+------------------------------------------------------------------+
double GetATRValue(ENUM_TIMEFRAMES tf, const int period, const int shift)
{
   MqlRates rates[];
   int copied = CopyRates(_Symbol, tf, shift, period + 2, rates);
   if(copied < period + 1)
      return 0.0;
   ArraySetAsSeries(rates, true);
   return ATRFromRates(rates, copied, period, 0);
}

double ATRFromRates(MqlRates &rates[], const int count, const int period, const int start)
{
   if(count <= start + period)
      return 0.0;

   double total = 0.0;
   int used = 0;
   for(int i = start; i < start + period && i + 1 < count; i++)
   {
      double tr1 = rates[i].high - rates[i].low;
      double tr2 = MathAbs(rates[i].high - rates[i + 1].close);
      double tr3 = MathAbs(rates[i].low - rates[i + 1].close);
      total += MathMax(tr1, MathMax(tr2, tr3));
      used++;
   }

   if(used <= 0)
      return 0.0;
   return total / (double)used;
}

double AverageClose(MqlRates &rates[], const int count, const int start, const int len)
{
   if(count <= start)
      return 0.0;

   int end = MinInt(count, start + len);
   double sum = 0.0;
   int used = 0;
   for(int i = start; i < end; i++)
   {
      sum += rates[i].close;
      used++;
   }

   if(used <= 0)
      return 0.0;
   return sum / (double)used;
}

double AverageVolume(MqlRates &rates[], const int count, const int start, const int len)
{
   if(count <= start)
      return 0.0;

   int end = MinInt(count, start + len);
   double sum = 0.0;
   int used = 0;
   for(int i = start; i < end; i++)
   {
      sum += BarVolume(rates[i]);
      used++;
   }

   if(used <= 0)
      return 0.0;
   return sum / (double)used;
}

double BarVolume(const MqlRates &bar)
{
   // Exchange/futures real volume is preferred by the book.  Most CFDs do not
   // publish it, so use broker tick volume only when real volume is unavailable.
   if(bar.real_volume > 0)
      return (double)bar.real_volume;
   return (double)bar.tick_volume;
}

double HighestHigh(MqlRates &rates[], const int count, const int start, const int len)
{
   if(count <= start)
      return 0.0;

   int end = MinInt(count, start + len);
   double value = -DBL_MAX;
   for(int i = start; i < end; i++)
      value = MathMax(value, rates[i].high);
   return value;
}

double LowestLow(MqlRates &rates[], const int count, const int start, const int len)
{
   if(count <= start)
      return 0.0;

   int end = MinInt(count, start + len);
   double value = DBL_MAX;
   for(int i = start; i < end; i++)
      value = MathMin(value, rates[i].low);
   return value;
}

int ClampInt(const int value, const int min_value, const int max_value)
{
   if(value < min_value)
      return min_value;
   if(value > max_value)
      return max_value;
   return value;
}

int MaxInt(const int a, const int b)
{
   return (a > b ? a : b);
}

int MinInt(const int a, const int b)
{
   return (a < b ? a : b);
}

double ClampDouble(const double value, const double min_value, const double max_value)
{
   if(value < min_value)
      return min_value;
   if(value > max_value)
      return max_value;
   return value;
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price, (int)_Digits);
}

//+------------------------------------------------------------------+

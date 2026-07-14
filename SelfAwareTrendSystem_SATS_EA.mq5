//+------------------------------------------------------------------+
//| SelfAwareTrendSystem_SATS_EA.mq5                                 |
//| MetaTrader 5 Expert Advisor                                      |
//|                                                                  |
//| Practical EA port of the TradingView Pine script:                 |
//| "Self-Aware Trend System [WillyAlgoTrader]"                       |
//|                                                                  |
//| Core ported logic:                                                |
//| - Efficiency/volatility/structure/momentum Trend Quality Index    |
//| - Adaptive SuperTrend-style bands                                 |
//| - Character-flip detection                                        |
//| - Score-gated buy/sell flips                                      |
//| - ATR/pivot based stop loss                                       |
//| - Fixed or dynamic R-multiple targets                             |
//| - Optional 3-leg entries: TP1, TP2, TP3                            |
//| - Ladder protection: TP1 -> BE, TP2 -> TP1 for the runner          |
//|                                                                  |
//| Notes:                                                            |
//| - Visual dashboard/self-learning UI from Pine is not ported.       |
//| - This file is for backtesting/forward testing first.              |
//| - Live trading is disabled by default.                             |
//+------------------------------------------------------------------+
#property strict
#property version   "1.01"
#property description "SATS EA: adaptive TQI trend flips with 3-leg TP ladder."

#include <Trade/Trade.mqh>

enum ENUM_SATS_PRESET
{
   SATS_AUTO = 0,
   SATS_CUSTOM = 1,
   SATS_SCALPING = 2,
   SATS_DEFAULT = 3,
   SATS_SWING = 4,
   SATS_CRYPTO_24_7 = 5
};

enum ENUM_SATS_TP_MODE
{
   SATS_TP_FIXED = 0,
   SATS_TP_DYNAMIC = 1
};

enum ENUM_SATS_LOT_MODE
{
   SATS_STATIC_LOT = 0,
   SATS_RISK_PERCENT = 1
};

input string             InpEAName                  = "SATS EA";
input ulong              InpMagicNumber             = 88201301;
input bool               InpEnableTrading           = false;
input bool               InpAllowTesterTrading      = true;
input ENUM_TIMEFRAMES    InpSignalTimeframe         = PERIOD_M15;
input int                InpHistoryBars             = 700;
input int                InpMaxSpreadPoints         = 350;
input int                InpSlippagePoints          = 30;
input bool               InpWeekdaysOnly            = true;
input bool               InpOneSameDirection        = true;

input ENUM_SATS_PRESET   InpPreset                  = SATS_AUTO;
input int                InpAtrLen                  = 13;
input double             InpBaseMult                = 2.0;
input bool               InpUseAdaptive             = true;
input int                InpErLength                = 20;
input double             InpAdaptStrength           = 0.5;
input int                InpAtrBaselineLen          = 100;

input bool               InpUseTqi                  = true;
input double             InpQualityStrength         = 0.4;
input double             InpQualityCurve            = 1.5;
input bool               InpSmoothMultipliers       = true;
input bool               InpUseAsymBands            = true;
input double             InpAsymStrength            = 0.5;
input bool               InpUseEffAtr               = true;
input bool               InpUseCharFlip             = true;
input int                InpCharFlipMinAge          = 5;
input double             InpCharFlipHigh            = 0.55;
input double             InpCharFlipLow             = 0.25;

input double             InpTqiWeightEr             = 0.35;
input double             InpTqiWeightVol            = 0.20;
input double             InpTqiWeightStruct         = 0.25;
input double             InpTqiWeightMom            = 0.20;
input int                InpTqiStructLen            = 20;
input int                InpTqiMomLen               = 10;

input int                InpPivotLen                = 3;
input int                InpRsiLen                  = 14;
input int                InpRsiOverbought           = 70;
input int                InpRsiOversold             = 30;
input int                InpRsiLookback             = 20;
input int                InpVolLen                  = 20;

input double             InpMinScore                = 40.0;
input double             InpMinTqi                  = 0.35;
input double             InpSlAtrMult               = 1.5;
input double             InpSlMaxDistAtr            = 4.0;
input ENUM_SATS_TP_MODE  InpTpMode                  = SATS_TP_DYNAMIC;
input double             InpTp1R                    = 1.0;
input double             InpTp2R                    = 2.0;
input double             InpTp3R                    = 3.0;
input int                InpTradeTimeoutBars        = 100;

input double             InpDynTqiWeight            = 0.6;
input double             InpDynVolWeight            = 0.4;
input double             InpDynMinScale             = 0.5;
input double             InpDynMaxScale             = 2.0;
input double             InpDynFloorR1              = 0.5;
input double             InpDynCeilR3               = 8.0;

input ENUM_SATS_LOT_MODE InpLotMode                 = SATS_STATIC_LOT;
input double             InpStaticLot               = 0.03;
input double             InpRiskPercent             = 5.0;
input bool               InpUseThreeLegs            = true;
input bool               InpDrawBands               = true;

CTrade trade;
datetime g_last_signal_bar = 0;
string PREFIX = "SATS_EA_";

struct SatsSignal
{
   bool     valid;
   int      side;       // 1 buy, -1 sell
   datetime time;
   double   entry;
   double   stop;
   double   tp1;
   double   tp2;
   double   tp3;
   double   tp1r;
   double   tp2r;
   double   tp3r;
   double   score;
   double   tqi;
   double   er;
   double   vol_z;
   double   vol_ratio;
   double   lower_band;
   double   upper_band;
};

double Clamp(double value, double low, double high)
{
   return MathMax(low, MathMin(high, value));
}

double SafeDiv(double num, double den, double fallback = 0.0)
{
   if(den == 0.0 || !MathIsValidNumber(num) || !MathIsValidNumber(den))
      return fallback;
   return num / den;
}

double MapClamp(double value, double in_low, double in_high, double out_low, double out_high)
{
   double ratio = Clamp(SafeDiv(value - in_low, in_high - in_low, 0.0), 0.0, 1.0);
   return out_low + ratio * (out_high - out_low);
}

double MapClampInv(double value, double in_low, double in_high, double out_high, double out_low)
{
   double ratio = Clamp(SafeDiv(value - in_low, in_high - in_low, 0.0), 0.0, 1.0);
   return out_high - ratio * (out_high - out_low);
}

double TickSize()
{
   double value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   return value > 0.0 ? value : _Point;
}

double NormalizePrice(double price)
{
   double tick = TickSize();
   if(tick <= 0.0)
      return NormalizeDouble(price, _Digits);
   return NormalizeDouble(MathRound(price / tick) * tick, _Digits);
}

double NormalizeVolume(double lots)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      step = 0.01;
   lots = MathMax(min_lot, MathMin(max_lot, lots));
   lots = MathFloor(lots / step + 0.0000001) * step;
   int digits = (int)MathMax(0, MathCeil(-MathLog10(step)));
   return NormalizeDouble(lots, digits);
}

bool IsWeekday(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.day_of_week >= 1 && dt.day_of_week <= 5;
}

bool IsNewSignalBar(datetime bar_time)
{
   if(bar_time <= 0 || bar_time == g_last_signal_bar)
      return false;
   g_last_signal_bar = bar_time;
   return true;
}

int TfMinutes(ENUM_TIMEFRAMES tf)
{
   int seconds = PeriodSeconds(tf);
   if(seconds <= 0)
      return 15;
   return seconds / 60;
}

ENUM_SATS_PRESET ResolvedPreset()
{
   if(InpPreset != SATS_AUTO)
      return InpPreset;
   int minutes = TfMinutes(InpSignalTimeframe);
   if(minutes <= 5)
      return SATS_SCALPING;
   if(minutes <= 240)
      return SATS_DEFAULT;
   return SATS_SWING;
}

void EffectiveParams(int &atr_len, double &base_mult, int &er_len, int &rsi_len, double &sl_mult)
{
   ENUM_SATS_PRESET preset = ResolvedPreset();
   atr_len = InpAtrLen;
   base_mult = InpBaseMult;
   er_len = InpErLength;
   rsi_len = InpRsiLen;
   sl_mult = InpSlAtrMult;

   if(preset == SATS_SCALPING)
   {
      atr_len = 10; base_mult = 1.5; er_len = 14; rsi_len = 9; sl_mult = 1.0;
   }
   else if(preset == SATS_DEFAULT)
   {
      atr_len = 14; base_mult = 2.0; er_len = 20; rsi_len = 14; sl_mult = 1.5;
   }
   else if(preset == SATS_SWING)
   {
      atr_len = 21; base_mult = 2.5; er_len = 30; rsi_len = 21; sl_mult = 2.0;
   }
   else if(preset == SATS_CRYPTO_24_7)
   {
      atr_len = 14; base_mult = 2.8; er_len = 20; rsi_len = 14; sl_mult = 2.0;
   }
}

bool LoadRates(MqlRates &rates[])
{
   ArrayResize(rates, 0);
   int count = MathMax(InpHistoryBars, 250);
   int copied = CopyRates(_Symbol, InpSignalTimeframe, 1, count, rates);
   if(copied < 220)
   {
      Print("SATS: not enough closed bars copied: ", copied);
      return false;
   }

   if(rates[0].time > rates[copied - 1].time)
   {
      for(int i = 0; i < copied / 2; i++)
      {
         MqlRates tmp = rates[i];
         rates[i] = rates[copied - 1 - i];
         rates[copied - 1 - i] = tmp;
      }
   }
   return true;
}

double SMA(double &arr[], int i, int len)
{
   if(i < 0 || len <= 0)
      return 0.0;
   int start = MathMax(0, i - len + 1);
   double sum = 0.0;
   int cnt = 0;
   for(int j = start; j <= i; j++)
   {
      sum += arr[j];
      cnt++;
   }
   return cnt > 0 ? sum / cnt : 0.0;
}

double StdDev(double &arr[], int i, int len)
{
   int start = MathMax(0, i - len + 1);
   int cnt = i - start + 1;
   if(cnt <= 1)
      return 0.0;
   double mean = SMA(arr, i, len);
   double sum = 0.0;
   for(int j = start; j <= i; j++)
      sum += MathPow(arr[j] - mean, 2.0);
   return MathSqrt(sum / cnt);
}

double RollingHighest(MqlRates &rates[], int i, int len)
{
   int start = MathMax(0, i - len + 1);
   double value = rates[start].high;
   for(int j = start + 1; j <= i; j++)
      value = MathMax(value, rates[j].high);
   return value;
}

double RollingLowest(MqlRates &rates[], int i, int len)
{
   int start = MathMax(0, i - len + 1);
   double value = rates[start].low;
   for(int j = start + 1; j <= i; j++)
      value = MathMin(value, rates[j].low);
   return value;
}

double RollingMax(double &arr[], int start, int end)
{
   start = MathMax(0, start);
   double value = arr[start];
   for(int j = start + 1; j <= end; j++)
      value = MathMax(value, arr[j]);
   return value;
}

double EfficiencyRatio(MqlRates &rates[], int i, int len)
{
   if(i < len)
      return 0.0;
   double change = MathAbs(rates[i].close - rates[i - len].close);
   double volatility = 0.0;
   for(int j = i - len + 1; j <= i; j++)
      volatility += MathAbs(rates[j].close - rates[j - 1].close);
   return Clamp(SafeDiv(change, volatility, 0.0), 0.0, 1.0);
}

void BuildIndicators(MqlRates &rates[], int n, SatsSignal &last_signal)
{
   last_signal.valid = false;

   int atr_len, er_len, rsi_len;
   double base_mult, sl_mult;
   EffectiveParams(atr_len, base_mult, er_len, rsi_len, sl_mult);

   double tr[], atr[], atr_base[], er[], atr_value[], vol_ratio[], volume[], vol_z[], rsi[];
   double lower_band[], upper_band[], active_sm[], passive_sm[], tqi[];
   int trend[];

   ArrayResize(tr, n);
   ArrayResize(atr, n);
   ArrayResize(atr_base, n);
   ArrayResize(er, n);
   ArrayResize(atr_value, n);
   ArrayResize(vol_ratio, n);
   ArrayResize(volume, n);
   ArrayResize(vol_z, n);
   ArrayResize(rsi, n);
   ArrayResize(lower_band, n);
   ArrayResize(upper_band, n);
   ArrayResize(active_sm, n);
   ArrayResize(passive_sm, n);
   ArrayResize(tqi, n);
   ArrayResize(trend, n);

   double gain_rma = 0.0, loss_rma = 0.0;
   for(int i = 0; i < n; i++)
   {
      double prev_close = i > 0 ? rates[i - 1].close : rates[i].close;
      tr[i] = MathMax(rates[i].high - rates[i].low, MathMax(MathAbs(rates[i].high - prev_close), MathAbs(rates[i].low - prev_close)));
      atr[i] = (i == 0 ? tr[i] : (atr[i - 1] * (atr_len - 1) + tr[i]) / atr_len);
      atr_base[i] = SMA(atr, i, InpAtrBaselineLen);
      er[i] = EfficiencyRatio(rates, i, er_len);
      atr_value[i] = InpUseEffAtr ? atr[i] * (0.5 + 0.5 * er[i]) : atr[i];
      vol_ratio[i] = SafeDiv(atr[i], atr_base[i], 1.0);
      volume[i] = (double)rates[i].tick_volume;

      if(i == 0)
      {
         rsi[i] = 50.0;
      }
      else
      {
         double change = rates[i].close - rates[i - 1].close;
         double gain = MathMax(change, 0.0);
         double loss = MathMax(-change, 0.0);
         gain_rma = (i == 1 ? gain : (gain_rma * (rsi_len - 1) + gain) / rsi_len);
         loss_rma = (i == 1 ? loss : (loss_rma * (rsi_len - 1) + loss) / rsi_len);
         double rs = loss_rma == 0.0 ? 100.0 : gain_rma / loss_rma;
         rsi[i] = 100.0 - 100.0 / (1.0 + rs);
      }

      double v_mean = SMA(volume, i, InpVolLen);
      double v_std = StdDev(volume, i, InpVolLen);
      vol_z[i] = v_std > 0.0 ? (volume[i] - v_mean) / v_std : 0.0;
   }

   double last_pivot_high = 0.0;
   double last_pivot_low = 0.0;
   bool has_pivot_high = false;
   bool has_pivot_low = false;
   int trend_start = 0;
   int warmup = MathMax(50, MathMax(MathMax(atr_len, InpAtrBaselineLen), MathMax(MathMax(er_len, rsi_len), MathMax(InpVolLen, MathMax(InpTqiMomLen, InpTqiStructLen))))) + 10;

   for(int i = 0; i < n; i++)
   {
      int pivot_index = i - InpPivotLen;
      if(pivot_index >= InpPivotLen)
      {
         bool ph = true;
         bool pl = true;
         for(int k = pivot_index - InpPivotLen; k <= pivot_index + InpPivotLen; k++)
         {
            if(rates[pivot_index].high < rates[k].high) ph = false;
            if(rates[pivot_index].low > rates[k].low) pl = false;
         }
         if(ph)
         {
            last_pivot_high = rates[pivot_index].high;
            has_pivot_high = true;
         }
         if(pl)
         {
            last_pivot_low = rates[pivot_index].low;
            has_pivot_low = true;
         }
      }

      double tqi_vol = MapClamp(vol_z[i], -1.0, 2.0, 0.0, 1.0);
      double hi = RollingHighest(rates, i, InpTqiStructLen);
      double lo = RollingLowest(rates, i, InpTqiStructLen);
      double price_pos = SafeDiv(rates[i].close - lo, hi - lo, 0.5);
      double tqi_struct = Clamp(MathAbs(price_pos - 0.5) * 2.0, 0.0, 1.0);
      double tqi_mom = 0.0;
      if(i >= InpTqiMomLen)
      {
         int up = 0, down = 0;
         for(int k = i - InpTqiMomLen + 1; k <= i; k++)
         {
            if(rates[k].close > rates[k - 1].close) up++;
            if(rates[k].close < rates[k - 1].close) down++;
         }
         double window_change = rates[i].close - rates[i - InpTqiMomLen].close;
         if(window_change > 0.0) tqi_mom = SafeDiv((double)up, InpTqiMomLen, 0.0);
         if(window_change < 0.0) tqi_mom = SafeDiv((double)down, InpTqiMomLen, 0.0);
      }
      double wsum = InpTqiWeightEr + InpTqiWeightVol + InpTqiWeightStruct + InpTqiWeightMom;
      tqi[i] = InpUseTqi ? Clamp(SafeDiv(er[i] * InpTqiWeightEr + tqi_vol * InpTqiWeightVol + tqi_struct * InpTqiWeightStruct + tqi_mom * InpTqiWeightMom, wsum, 0.5), 0.0, 1.0) : 0.5;

      int prev_trend = i > 0 ? trend[i - 1] : 1;
      double legacy_adapt = InpUseAdaptive ? 1.0 + InpAdaptStrength * (0.5 - er[i]) : 1.0;
      double quality_deviation = InpUseTqi ? MathPow(1.0 - tqi[i], InpQualityCurve) : 0.5;
      double tqi_mult = 1.0 - InpQualityStrength + InpQualityStrength * (0.6 + 0.8 * quality_deviation);
      double sym_mult = base_mult * legacy_adapt * tqi_mult;
      double active_raw = sym_mult;
      double passive_raw = sym_mult;
      if(InpUseTqi && InpUseAsymBands)
      {
         double asym_tighten = 1.0 - InpAsymStrength * tqi[i] * 0.3;
         double asym_widen = 1.0 + InpAsymStrength * tqi[i] * 0.4;
         active_raw = sym_mult * asym_tighten;
         passive_raw = sym_mult * asym_widen;
      }

      if(i == 0)
      {
         active_sm[i] = active_raw;
         passive_sm[i] = passive_raw;
      }
      else
      {
         double alpha = InpSmoothMultipliers ? 0.15 : 1.0;
         active_sm[i] = active_sm[i - 1] * (1.0 - alpha) + active_raw * alpha;
         passive_sm[i] = passive_sm[i - 1] * (1.0 - alpha) + passive_raw * alpha;
      }

      double lower_mult = prev_trend == 1 ? active_sm[i] : passive_sm[i];
      double upper_mult = prev_trend == 1 ? passive_sm[i] : active_sm[i];
      double lower_raw = rates[i].close - lower_mult * atr_value[i];
      double upper_raw = rates[i].close + upper_mult * atr_value[i];

      if(i == 0)
      {
         lower_band[i] = lower_raw;
         upper_band[i] = upper_raw;
      }
      else
      {
         double prev_close = rates[i - 1].close;
         lower_band[i] = prev_close > lower_band[i - 1] ? MathMax(lower_raw, lower_band[i - 1]) : lower_raw;
         upper_band[i] = prev_close < upper_band[i - 1] ? MathMin(upper_raw, upper_band[i - 1]) : upper_raw;
      }

      bool price_flip_up = i > 0 && prev_trend == -1 && rates[i].close > upper_band[i - 1];
      bool price_flip_down = i > 0 && prev_trend == 1 && rates[i].close < lower_band[i - 1];
      int trend_age = i - trend_start;
      int char_window = MathMax(InpCharFlipMinAge, 3);
      double tqi_window_high = i >= char_window - 1 ? RollingMax(tqi, i - char_window + 1, i) : tqi[i];
      bool char_base = InpUseCharFlip && InpUseTqi && trend_age >= InpCharFlipMinAge && tqi_window_high > InpCharFlipHigh && tqi[i] < InpCharFlipLow && i >= char_window;
      bool char_down = char_base && prev_trend == 1 && rates[i].close < rates[i - char_window].close;
      bool char_up = char_base && prev_trend == -1 && rates[i].close > rates[i - char_window].close;
      bool final_up = price_flip_up || char_up;
      bool final_down = price_flip_down || char_down;
      trend[i] = final_up ? 1 : (final_down ? -1 : prev_trend);
      if(trend[i] != prev_trend)
         trend_start = i;

      bool flip_up = i > 0 && trend[i] == 1 && prev_trend == -1;
      bool flip_down = i > 0 && trend[i] == -1 && prev_trend == 1;
      bool is_buy_score = trend[i] == 1;
      double dir_move = 0.0;
      if(i >= 3)
         dir_move = is_buy_score ? rates[i - 3].close - rates[i].close : rates[i].close - rates[i - 3].close;
      double atr_now = atr_value[i];
      double mom_score = MapClamp(SafeDiv(dir_move, atr_now, 0.0), 0.3, 2.0, 0.0, 17.0);
      double er_score = MapClamp(er[i], 0.15, 0.7, 0.0, 17.0);
      double volume_score = MapClamp(vol_z[i], 0.0, 3.0, 0.0, 17.0);

      double rsi_low = rsi[i];
      double rsi_high = rsi[i];
      int rs = MathMax(0, i - InpRsiLookback + 1);
      for(int k = rs; k <= i; k++)
      {
         rsi_low = MathMin(rsi_low, rsi[k]);
         rsi_high = MathMax(rsi_high, rsi[k]);
      }
      double rsi_depth = is_buy_score ? MathMax(0.0, InpRsiOversold - rsi_low) : MathMax(0.0, rsi_high - InpRsiOverbought);
      double rsi_score = MapClamp(rsi_depth, 0.0, 15.0, 0.0, 17.0);

      double pivot_dist = 0.0;
      if(is_buy_score && has_pivot_low) pivot_dist = MathAbs(rates[i].close - last_pivot_low);
      if(!is_buy_score && has_pivot_high) pivot_dist = MathAbs(last_pivot_high - rates[i].close);
      double struct_score = MapClampInv(SafeDiv(pivot_dist, atr_now, 0.0), 0.0, 1.5, 16.0, 6.0);

      double break_depth = 0.0;
      if(i > 0)
         break_depth = is_buy_score ? MathMax(0.0, upper_band[i - 1] - rates[i - 1].close) : MathMax(0.0, rates[i - 1].close - lower_band[i - 1]);
      double break_score = MapClamp(SafeDiv(break_depth, atr_now, 0.0), 0.0, 1.0, 0.0, 16.0);
      double score = mom_score + er_score + volume_score + rsi_score + struct_score + break_score;

      if(i >= warmup && (flip_up || flip_down) && i == n - 1)
      {
         int side = flip_up ? 1 : -1;
         if(score >= InpMinScore && tqi[i] >= InpMinTqi)
         {
            double stop = 0.0;
            double risk = 0.0;
            if(side == 1)
            {
               double sl_base = has_pivot_low ? last_pivot_low : rates[i].low;
               double raw_sl = sl_base - sl_mult * atr_now;
               double min_sl = rates[i].close - sl_mult * atr_now;
               stop = MathMin(raw_sl, min_sl);
               stop = MathMax(stop, rates[i].close - MathMax(InpSlMaxDistAtr, sl_mult) * atr_now);
               risk = rates[i].close - stop;
            }
            else
            {
               double sl_base = has_pivot_high ? last_pivot_high : rates[i].high;
               double raw_sl = sl_base + sl_mult * atr_now;
               double min_sl = rates[i].close + sl_mult * atr_now;
               stop = MathMax(raw_sl, min_sl);
               stop = MathMin(stop, rates[i].close + MathMax(InpSlMaxDistAtr, sl_mult) * atr_now);
               risk = stop - rates[i].close;
            }

            if(risk > 0.0)
            {
               double tp1r = InpTp1R, tp2r = InpTp2R, tp3r = InpTp3R;
               if(InpTpMode == SATS_TP_DYNAMIC)
               {
                  double tqi_comp = Clamp(tqi[i], 0.0, 1.0);
                  double vol_comp = Clamp(MapClamp(vol_ratio[i], 0.5, 2.0, 0.0, 1.0), 0.0, 1.0);
                  double w = InpDynTqiWeight + InpDynVolWeight;
                  double raw_scale = SafeDiv(tqi_comp * InpDynTqiWeight + vol_comp * InpDynVolWeight, w, 1.0);
                  double scale = InpDynMinScale + raw_scale * (InpDynMaxScale - InpDynMinScale);
                  tp1r = Clamp(InpTp1R * scale, MathMin(InpDynFloorR1, InpDynCeilR3), InpDynCeilR3);
                  tp2r = Clamp(InpTp2R * scale, MathMin(InpDynFloorR1 * SafeDiv(InpTp2R, MathMax(InpTp1R, 0.01), 2.0), InpDynCeilR3), InpDynCeilR3);
                  tp3r = Clamp(InpTp3R * scale, MathMin(InpDynFloorR1 * SafeDiv(InpTp3R, MathMax(InpTp1R, 0.01), 3.0), InpDynCeilR3), InpDynCeilR3);
               }
               if(tp1r > tp2r) { double t = tp1r; tp1r = tp2r; tp2r = t; }
               if(tp2r > tp3r) { double t = tp2r; tp2r = tp3r; tp3r = t; }
               if(tp1r > tp2r) { double t = tp1r; tp1r = tp2r; tp2r = t; }

               last_signal.valid = true;
               last_signal.side = side;
               last_signal.time = rates[i].time;
               last_signal.entry = rates[i].close;
               last_signal.stop = NormalizePrice(stop);
               last_signal.tp1 = NormalizePrice(side == 1 ? rates[i].close + risk * tp1r : rates[i].close - risk * tp1r);
               last_signal.tp2 = NormalizePrice(side == 1 ? rates[i].close + risk * tp2r : rates[i].close - risk * tp2r);
               last_signal.tp3 = NormalizePrice(side == 1 ? rates[i].close + risk * tp3r : rates[i].close - risk * tp3r);
               last_signal.tp1r = tp1r;
               last_signal.tp2r = tp2r;
               last_signal.tp3r = tp3r;
               last_signal.score = score;
               last_signal.tqi = tqi[i];
               last_signal.er = er[i];
               last_signal.vol_z = vol_z[i];
               last_signal.vol_ratio = vol_ratio[i];
               last_signal.lower_band = NormalizePrice(lower_band[i]);
               last_signal.upper_band = NormalizePrice(upper_band[i]);
            }
         }
      }
   }

   if(InpDrawBands && n > 0)
   {
      DrawLine("LOWER", lower_band[n - 1], clrDeepSkyBlue);
      DrawLine("UPPER", upper_band[n - 1], clrTomato);
   }
}

void DrawLine(string name, double price, color c)
{
   string obj = PREFIX + name;
   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, obj, OBJPROP_PRICE, NormalizePrice(price));
   ObjectSetInteger(0, obj, OBJPROP_COLOR, c);
   ObjectSetInteger(0, obj, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, obj, OBJPROP_WIDTH, 1);
}

bool SpreadOk()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread <= InpMaxSpreadPoints)
      return true;
   Print("SATS blocked: spread ", spread, " > ", InpMaxSpreadPoints);
   return false;
}

bool HasSameDirectionPosition(int side)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if(side == 1 && type == POSITION_TYPE_BUY)
         return true;
      if(side == -1 && type == POSITION_TYPE_SELL)
         return true;
   }
   return false;
}

bool CanSendOrders()
{
   if((bool)MQLInfoInteger(MQL_TESTER) && InpAllowTesterTrading)
      return true;
   return InpEnableTrading;
}

double LotForRisk(double entry, double stop)
{
   double total_lot = InpStaticLot;
   if(InpLotMode == SATS_RISK_PERCENT)
   {
      double risk_money = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
      double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_size = TickSize();
      double risk_ticks = MathAbs(entry - stop) / tick_size;
      double money_per_lot = risk_ticks * tick_value;
      if(money_per_lot > 0.0)
         total_lot = risk_money / money_per_lot;
   }
   return NormalizeVolume(total_lot);
}

void StoreTicketData(ulong ticket, int leg, double entry, double initial_sl, double tp1, double tp2)
{
   string base = PREFIX + IntegerToString((int)ticket) + "_";
   GlobalVariableSet(base + "LEG", (double)leg);
   GlobalVariableSet(base + "ENTRY", entry);
   GlobalVariableSet(base + "INIT_SL", initial_sl);
   GlobalVariableSet(base + "TP1", tp1);
   GlobalVariableSet(base + "TP2", tp2);
}

double Gv(ulong ticket, string key, double fallback)
{
   string name = PREFIX + IntegerToString((int)ticket) + "_" + key;
   if(GlobalVariableCheck(name))
      return GlobalVariableGet(name);
   return fallback;
}

void ManageOpenPositions()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      int side = type == POSITION_TYPE_BUY ? 1 : -1;
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl = PositionGetDouble(POSITION_SL);
      double current_tp = PositionGetDouble(POSITION_TP);
      int leg = (int)Gv(ticket, "LEG", 0);
      double tp1 = Gv(ticket, "TP1", 0.0);
      double tp2 = Gv(ticket, "TP2", 0.0);
      if(tp1 <= 0.0 || tp2 <= 0.0)
         continue;

      bool hit_tp1 = side == 1 ? bid >= tp1 : ask <= tp1;
      bool hit_tp2 = side == 1 ? bid >= tp2 : ask <= tp2;
      double new_sl = current_sl;

      if(hit_tp1 && (leg == 2 || leg == 3))
      {
         if(side == 1 && (current_sl < entry || current_sl == 0.0)) new_sl = entry;
         if(side == -1 && (current_sl > entry || current_sl == 0.0)) new_sl = entry;
      }
      if(hit_tp2 && leg == 3)
      {
         if(side == 1 && current_sl < tp1) new_sl = tp1;
         if(side == -1 && current_sl > tp1) new_sl = tp1;
      }

      new_sl = NormalizePrice(new_sl);
      if(new_sl != current_sl && new_sl > 0.0)
      {
         if(trade.PositionModify(ticket, new_sl, current_tp))
            Print("SATS ladder: ticket ", ticket, " SL moved to ", DoubleToString(new_sl, _Digits));
         else
            Print("SATS ladder failed for ticket ", ticket, ": ", trade.ResultRetcodeDescription());
      }
   }
}

bool PlaceLeg(int side, double lot, double sl, double tp, int leg, const SatsSignal &sig)
{
   string comment = StringFormat("SATS L%d S%.0f TQI%.2f", leg, sig.score, sig.tqi);
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   bool ok = false;
   if(side == 1)
      ok = trade.Buy(lot, _Symbol, 0.0, sl, tp, comment);
   else
      ok = trade.Sell(lot, _Symbol, 0.0, sl, tp, comment);

   if(!ok)
   {
      Print("SATS order failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      return false;
   }
   ulong ticket = trade.ResultOrder();
   if(ticket == 0)
      ticket = trade.ResultDeal();
   if(ticket > 0)
      StoreTicketData(ticket, leg, sig.entry, sig.stop, sig.tp1, sig.tp2);
   Print("SATS placed ", side == 1 ? "BUY" : "SELL", " leg ", leg, " lot=", lot, " SL=", sl, " TP=", tp, " ticket=", ticket);
   return true;
}

void PlaceSignal(const SatsSignal &sig)
{
   if(!CanSendOrders())
   {
      PrintFormat("SATS signal %s blocked because live trading is disabled. Enable InpEnableTrading for live charts, or keep InpAllowTesterTrading=true for backtests. score=%.1f tqi=%.2f entry=%.5f sl=%.5f tp1=%.5f tp2=%.5f tp3=%.5f",
                  sig.side == 1 ? "BUY" : "SELL", sig.score, sig.tqi, sig.entry, sig.stop, sig.tp1, sig.tp2, sig.tp3);
      return;
   }
   if(!(bool)MQLInfoInteger(MQL_TESTER) && (!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)))
   {
      Print("SATS blocked: terminal or EA auto-trading is disabled.");
      return;
   }
   if(!SpreadOk())
      return;
   if(InpOneSameDirection && HasSameDirectionPosition(sig.side))
   {
      Print("SATS blocked: existing same-direction position for this EA.");
      return;
   }

   double total_lot = LotForRisk(sig.entry, sig.stop);
   int legs = InpUseThreeLegs ? 3 : 1;
   double leg_lot = NormalizeVolume(total_lot / legs);
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(leg_lot < min_lot)
      leg_lot = min_lot;

   if(InpUseThreeLegs)
   {
      PlaceLeg(sig.side, leg_lot, sig.stop, sig.tp1, 1, sig);
      PlaceLeg(sig.side, leg_lot, sig.stop, sig.tp2, 2, sig);
      PlaceLeg(sig.side, leg_lot, sig.stop, sig.tp3, 3, sig);
   }
   else
   {
      PlaceLeg(sig.side, total_lot, sig.stop, sig.tp3, 3, sig);
   }
}

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   Print(InpEAName, " initialized on ", _Symbol, " ", EnumToString(InpSignalTimeframe),
         ". Live trading=", InpEnableTrading,
         ". Tester override=", InpAllowTesterTrading,
         ". MinScore=", InpMinScore,
         ". MinTQI=", InpMinTqi);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   ObjectDelete(0, PREFIX + "LOWER");
   ObjectDelete(0, PREFIX + "UPPER");
}

void OnTick()
{
   ManageOpenPositions();

   MqlRates rates[];
   if(!LoadRates(rates))
      return;

   int n = ArraySize(rates);
   if(n < 220)
      return;
   datetime closed_bar_time = rates[n - 1].time;
   if(!IsNewSignalBar(closed_bar_time))
      return;
   if(InpWeekdaysOnly && !IsWeekday(closed_bar_time))
   {
      Print("SATS blocked: weekend bar.");
      return;
   }

   SatsSignal sig;
   BuildIndicators(rates, n, sig);
   if(!sig.valid)
   {
      Print("SATS scan: no valid signal on closed bar ", TimeToString(closed_bar_time));
      return;
   }

   PrintFormat("SATS valid %s | score=%.1f tqi=%.2f er=%.2f volZ=%.2f entry=%.5f sl=%.5f tp1=%.5f tp2=%.5f tp3=%.5f",
               sig.side == 1 ? "BUY" : "SELL", sig.score, sig.tqi, sig.er, sig.vol_z, sig.entry, sig.stop, sig.tp1, sig.tp2, sig.tp3);
   PlaceSignal(sig);
}

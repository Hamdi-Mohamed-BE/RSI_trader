#property copyright "XAU Weakness multi-timeframe bias research EA"
#property version   "1.00"
#property strict

#include "AAA_Final_Common.mqh"

enum ENUM_XAU_BIAS_MODE
{
   XAU_BIAS_NONE=0,
   XAU_BIAS_H1=1,
   XAU_BIAS_H4=2,
   XAU_BIAS_D1=3,
   XAU_BIAS_ANY_OF_THREE=4,
   XAU_BIAS_MAJORITY_OF_THREE=5,
   XAU_BIAS_ALL_THREE=6
};

input group "Trading"
input bool InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long InpMagic=4080402;
input int InpMaxSpreadPoints=0;
input int InpMaximumDeviationPoints=50;

input group "Original XAU Weakness logic"
input double InpWeaknessATRImpulse=2.0;
input double InpRewardRisk=2.0;
input int InpPendingExpiryBars=8;

input group "Research multi-timeframe bias"
input ENUM_XAU_BIAS_MODE InpBuyBiasMode=XAU_BIAS_NONE;
input bool InpApplySymmetricBiasToSells=false;
input int InpBiasEMAPeriod=50;
input int InpBiasSlopeBars=3;

datetime g_last_bar=0;
int g_h1_ema=INVALID_HANDLE;
int g_h4_ema=INVALID_HANDLE;
int g_d1_ema=INVALID_HANDLE;

bool SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

bool LoadRates(const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);
   return CopyRates(_Symbol,timeframe,0,count,rates)==count;
}

int TimeframeBias(const ENUM_TIMEFRAMES timeframe,const int handle)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int needed=InpBiasSlopeBars+3;
   if(CopyRates(_Symbol,timeframe,0,needed,rates)!=needed) return 0;
   double recent[],older[];
   if(CopyBuffer(handle,0,1,1,recent)!=1 || CopyBuffer(handle,0,1+InpBiasSlopeBars,1,older)!=1) return 0;
   if(rates[1].close>recent[0] && recent[0]>older[0]) return 1;
   if(rates[1].close<recent[0] && recent[0]<older[0]) return -1;
   return 0;
}

bool BiasPasses(const int direction)
{
   if(InpBuyBiasMode==XAU_BIAS_NONE) return true;
   if(direction<0 && !InpApplySymmetricBiasToSells) return true;
   int wanted=(direction>0 ? 1 : -1);
   int h1=TimeframeBias(PERIOD_H1,g_h1_ema);
   int h4=TimeframeBias(PERIOD_H4,g_h4_ema);
   int d1=TimeframeBias(PERIOD_D1,g_d1_ema);
   if(InpBuyBiasMode==XAU_BIAS_H1) return h1==wanted;
   if(InpBuyBiasMode==XAU_BIAS_H4) return h4==wanted;
   if(InpBuyBiasMode==XAU_BIAS_D1) return d1==wanted;
   int aligned=(h1==wanted ? 1 : 0)+(h4==wanted ? 1 : 0)+(d1==wanted ? 1 : 0);
   if(InpBuyBiasMode==XAU_BIAS_ANY_OF_THREE) return aligned>=1;
   if(InpBuyBiasMode==XAU_BIAS_MAJORITY_OF_THREE) return aligned>=2;
   return aligned==3;
}

void RunXAUWeakness()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates r[];
   if(!LoadRates(PERIOD_M15,36,r)) return;
   double atr=AAA_ATR(_Symbol,PERIOD_M15,14,1);
   if(atr<=0.0) return;
   double tolerance=0.20*atr;
   int first_high=-1,second_high=-1,first_low=-1,second_low=-1;
   for(int newer=4;newer<=16;newer++)
   {
      for(int older=newer+4;older<=MathMin(newer+16,30);older++)
      {
         if(first_high<0 && MathAbs(r[newer].high-r[older].high)<=tolerance)
         {
            second_high=newer;
            first_high=older;
         }
         if(first_low<0 && MathAbs(r[newer].low-r[older].low)<=tolerance)
         {
            second_low=newer;
            first_low=older;
         }
      }
   }
   datetime expiry=TimeCurrent()+InpPendingExpiryBars*15*60;
   if(first_high>0 && BiasPasses(1))
   {
      double resistance=MathMax(r[first_high].high,r[second_high].high);
      double range_low=DBL_MAX;
      for(int index=1;index<=first_high;index++) range_low=MathMin(range_low,r[index].low);
      double impulse=r[first_high+1].close-r[MathMin(first_high+12,35)].open;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,resistance+0.05*atr,range_low-0.05*atr,
                         InpRewardRisk,InpRiskPercent,InpMagic,expiry,"XAU weakness bias buy");
   }
   else if(first_low>0 && BiasPasses(-1))
   {
      double support=MathMin(r[first_low].low,r[second_low].low);
      double range_high=-DBL_MAX;
      for(int index=1;index<=first_low;index++) range_high=MathMax(range_high,r[index].high);
      double impulse=r[MathMin(first_low+12,35)].open-r[first_low+1].close;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,support-0.05*atr,range_high+0.05*atr,
                         InpRewardRisk,InpRiskPercent,InpMagic,expiry,"XAU weakness bias sell");
   }
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpWeaknessATRImpulse<=0.0 || InpRewardRisk<=0.0 ||
      InpBiasEMAPeriod<2 || InpBiasSlopeBars<1 || InpPendingExpiryBars<1)
      return INIT_PARAMETERS_INCORRECT;
   g_h1_ema=iMA(_Symbol,PERIOD_H1,InpBiasEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h4_ema=iMA(_Symbol,PERIOD_H4,InpBiasEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_d1_ema=iMA(_Symbol,PERIOD_D1,InpBiasEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_h1_ema==INVALID_HANDLE || g_h4_ema==INVALID_HANDLE || g_d1_ema==INVALID_HANDLE) return INIT_FAILED;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_last_bar=iTime(_Symbol,PERIOD_M15,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_h1_ema!=INVALID_HANDLE) IndicatorRelease(g_h1_ema);
   if(g_h4_ema!=INVALID_HANDLE) IndicatorRelease(g_h4_ema);
   if(g_d1_ema!=INVALID_HANDLE) IndicatorRelease(g_d1_ema);
}

void OnTick()
{
   RunXAUWeakness();
}

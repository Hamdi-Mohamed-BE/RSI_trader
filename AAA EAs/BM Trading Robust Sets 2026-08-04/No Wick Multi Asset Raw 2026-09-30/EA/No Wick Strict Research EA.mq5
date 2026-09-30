#property strict
#property version "1.00"
#property description "Research-only no-wick retest; refuses non-tester execution."
input bool InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpRewardRisk=1.0;
input long InpMagic=1093007;
input bool InpAdaptivePortfolioControls=false;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input int InpSignalMode=0; // 0=strict flat wick, 1=any-colour-matched-candle control
input int InpTrendFast=50;
input int InpTrendSlow=200;
input int InpSwingLookback=100;
input int InpPivotWidth=2;
input int InpExpiryBars=20;
#include "../../No Wick Candle Raw 2026-09-25/EA/AAA_Final_Common.mqh"
datetime g_nws_last_bar=0;
int fast_handle=INVALID_HANDLE,slow_handle=INVALID_HANDLE;
long signals=0,placed=0,invalid_geometry=0,missing_pivot=0,rejected=0,expired=0;
double tick_size=0;

int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)) {Print("RESEARCH ONLY: live/demo chart execution refused");return INIT_FAILED;}
 if(InpRiskPercent<=0 || InpRewardRisk<=0 || InpPivotWidth<1 || InpSwingLookback<2*InpPivotWidth+1 || InpExpiryBars<1) return INIT_PARAMETERS_INCORRECT;
 tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 if(tick_size<=0)tick_size=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
 fast_handle=iMA(_Symbol,InpSignalTimeframe,InpTrendFast,0,MODE_EMA,PRICE_CLOSE);
 slow_handle=iMA(_Symbol,InpSignalTimeframe,InpTrendSlow,0,MODE_EMA,PRICE_CLOSE);
 if(fast_handle==INVALID_HANDLE || slow_handle==INVALID_HANDLE || tick_size<=0)return INIT_FAILED;
 PrintFormat("NW_SPEC symbol=%s description=%s digits=%d point=%.10f tick=%.10f contract=%.4f minlot=%.8f step=%.8f maxlot=%.4f stops=%d freeze=%d account_currency=%s leverage=%d server=%s",
 _Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS),SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick_size,
 SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),
 (int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL),AccountInfoString(ACCOUNT_CURRENCY),(int)AccountInfoInteger(ACCOUNT_LEVERAGE),AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 PrintFormat("NW_STATS signals=%I64d placed=%I64d invalid_geometry=%I64d missing_pivot=%I64d rejected=%I64d expired=%I64d",signals,placed,invalid_geometry,missing_pivot,rejected,expired);
 IndicatorRelease(fast_handle);IndicatorRelease(slow_handle);
}
double PriceTick(double value) {return AAA_Price(_Symbol,MathRound(value/tick_size)*tick_size);}
void ExpireOrders()
{
 for(int i=OrdersTotal()-1;i>=0;i--)
 {
  ulong ticket=OrderGetTicket(i);
  if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic)continue;
  if(TimeCurrent()-(datetime)OrderGetInteger(ORDER_TIME_SETUP)<InpExpiryBars*PeriodSeconds(InpSignalTimeframe))continue;
  AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
  if(AAA_Trade.OrderDelete(ticket))expired++;
 }
}
bool RecentPivot(MqlRates &r[],int direction,double &level)
{
 int width=InpPivotWidth;
 for(int i=width+1;i<=InpSwingLookback;i++)
 {
  bool good=true;
  double candidate=direction>0?r[i].low:r[i].high;
  for(int j=1;j<=width;j++)
  {
   if(direction>0 && (candidate>=r[i-j].low || candidate>=r[i+j].low))good=false;
   if(direction<0 && (candidate<=r[i-j].high || candidate<=r[i+j].high))good=false;
  }
  if(good){level=candidate;return true;}
 }
 return false;
}
void OnTick()
{
 if(!InpEnableTrading)return;
 ExpireOrders();
 if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_nws_last_bar) || AAA_HasExposure(_Symbol,InpMagic))return;
 if(BarsCalculated(slow_handle)<InpTrendSlow+2)return;
 double fast=AAA_BufferValue(fast_handle,0,1),slow=AAA_BufferValue(slow_handle,0,1);
 if(fast==EMPTY_VALUE || slow==EMPTY_VALUE || fast<=0 || slow<=0)return;
 MqlRates r[];ArraySetAsSeries(r,true);
 int need=InpSwingLookback+InpPivotWidth+2;
 if(CopyRates(_Symbol,InpSignalTimeframe,0,need,r)!=need)return;
 int direction=0;
 if(r[1].close>slow && fast>slow && r[1].close>r[1].open)direction=1;
 if(r[1].close<slow && fast<slow && r[1].close<r[1].open)direction=-1;
 if(direction==0)return;
 if(InpSignalMode==0 && (direction>0?r[1].open-r[1].low:r[1].high-r[1].open)>tick_size*0.1)return;
 signals++;
 double pivot=0;
 if(!RecentPivot(r,direction,pivot)){missing_pivot++;return;}
 double entry=PriceTick(r[1].open),sl=PriceTick(pivot-direction*tick_size);
 double risk=direction*(entry-sl);
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
 if(risk<=0 || risk<minimum || (direction>0?(entry>=q.ask || q.ask-entry<minimum):(entry<=q.bid || entry-q.bid<minimum))) {invalid_geometry++;return;}
 double tp=PriceTick(entry+direction*risk*InpRewardRisk);
 double lots=AAA_LotsForRisk(_Symbol,direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,sl,InpRiskPercent);
 if(lots<=0){rejected++;return;}
 AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);AAA_Trade.SetTypeFillingBySymbol(_Symbol);
 string label=StringFormat("NW %s s%I64d",InpSignalMode==0?"strict":"control",(long)r[1].time);
 bool ok=direction>0?AAA_Trade.BuyLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,label):AAA_Trade.SellLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,label);
 if(ok){placed++;PrintFormat("NW_SIGNAL time=%s signal=%s side=%d entry=%.10f sl=%.10f tp=%.10f pivot=%.10f volume=%.8f",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(r[1].time,TIME_DATE|TIME_SECONDS),direction,entry,sl,tp,pivot,lots);}
 else rejected++;
}

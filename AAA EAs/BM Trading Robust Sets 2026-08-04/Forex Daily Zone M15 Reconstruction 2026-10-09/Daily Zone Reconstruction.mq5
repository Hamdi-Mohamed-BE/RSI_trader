#property strict
#property version "1.00"
#property description "TESTER ONLY: approved mechanical proxy, not Revelio's unpublished algorithm."
#include <Trade/Trade.mqh>

input double InpRiskPercent=0.5;
input bool InpHighWaterSizing=false;
input double InpStopBufferPips=6.0;
input double InpRewardRisk=2.0;
input int InpLookbackCalendarDays=730;
input double InpMinZonePips=5.0;
input double InpMaxZonePips=60.0;
input long InpMagic=26100915;
input int InpDeviationPoints=30;
input datetime InpTradingFrom=D'2023.10.09 00:00:00';

struct Pivot {double price;datetime time;};
struct Zone {double low;double high;int touches;};
Pivot pivots[];
Zone zones[];
CTrade trade;
datetime last_m15=0,last_daily=0;
double high_balance=0;
long rebuilds=0,signals=0,placed=0,rejected=0,small=0,invalid=0,occupied=0;

double Pip(){return _Point*((_Digits==3 || _Digits==5)?10:1);}
double RoundPrice(double price){double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(price/step)*step,_Digits);}
double BodyHigh(MqlRates &r){return MathMax(r.open,r.close);}
double BodyLow(MqlRates &r){return MathMin(r.open,r.close);}
void AddPivot(double price,datetime time)
{
   int size=ArraySize(pivots);ArrayResize(pivots,size+1);
   pivots[size].price=price;pivots[size].time=time;
}

bool BuildZones(datetime daily)
{
   // Only completed D1 bars; two completed bars on each side confirm a swing.
   MqlRates bars[];
   int count=CopyRates(_Symbol,PERIOD_D1,daily-InpLookbackCalendarDays*86400,daily-1,bars);
   datetime cutoff=daily-InpLookbackCalendarDays*86400;
   if(count<400 || bars[0].time>cutoff+7*86400)
   {Print("ZONE_HISTORY_INSUFFICIENT count=",count);return false;}
   ArrayResize(pivots,0);ArrayResize(zones,0);
   for(int i=2;i<count-2;i++)
   {
      double bh=BodyHigh(bars[i]),bl=BodyLow(bars[i]);
      bool top=true,bottom=true,strict_top=false,strict_bottom=false;
      for(int k=-2;k<=2;k++)
      {
         if(k==0)continue;
         double hh=BodyHigh(bars[i+k]),ll=BodyLow(bars[i+k]);
         if(bh<hh)top=false;if(bl>ll)bottom=false;
         if(bh>hh)strict_top=true;if(bl<ll)strict_bottom=true;
      }
      if(top && strict_top)AddPivot(bh,bars[i].time);
      if(bottom && strict_bottom && (!top || MathAbs(bh-bl)>_Point/2))AddPivot(bl,bars[i].time);
   }
   // Frozen complete-link proxy: sort body-swing prices, then greedily take
   // disjoint bands spanning no more than 60 pips. No results-driven fitting.
   for(int i=1;i<ArraySize(pivots);i++)
   {
      Pivot p=pivots[i];int j=i-1;
      while(j>=0 && pivots[j].price>p.price){pivots[j+1]=pivots[j];j--;}
      pivots[j+1]=p;
   }
   int i=0;
   while(i<ArraySize(pivots))
   {
      int j=i+1;
      while(j<ArraySize(pivots) && pivots[j].price-pivots[i].price<=InpMaxZonePips*Pip()+_Point/2)j++;
      int touches=0;
      for(int k=i;k<j;k++)
      {
         bool distinct=true;
         for(int q=i;q<k;q++)if(pivots[q].time==pivots[k].time){distinct=false;break;}
         if(distinct)touches++;
      }
      if(touches>=3)
      {
         double low=pivots[i].price,high=pivots[j-1].price;
         if(high-low<InpMinZonePips*Pip())
         {double center=(low+high)/2;low=center-InpMinZonePips*Pip()/2;high=center+InpMinZonePips*Pip()/2;}
         int z=ArraySize(zones);ArrayResize(zones,z+1);
         zones[z].low=low;zones[z].high=high;zones[z].touches=touches;
      }
      i=j;
   }
   rebuilds++;
   if(rebuilds==1)Print("ZONE_WARMUP first=",TimeToString(bars[0].time,TIME_DATE)," last=",TimeToString(bars[count-1].time,TIME_DATE)," bars=",count," pivots=",ArraySize(pivots)," zones=",ArraySize(zones));
   return true;
}

bool HavePosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;
   }
   return false;
}

double LotsForRisk(ENUM_ORDER_TYPE side,double entry,double stop)
{
   double one_lot=0;
   if(!OrderCalcProfit(side,_Symbol,1.0,entry,stop,one_lot) || one_lot>=0)return 0;
   double reference=InpHighWaterSizing?high_balance:AccountInfoDouble(ACCOUNT_BALANCE);
   double lots=reference*InpRiskPercent/100/MathAbs(one_lot);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   lots=MathFloor((MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-10)/step)*step;
   if(lots<minimum-1e-10)return 0; // Never raise the size above the risk budget.
   double margin=0;
   if(!OrderCalcMargin(side,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return 0;
   return NormalizeDouble(lots,8);
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
   if(InpRiskPercent<=0 || InpRewardRisk<=0 || InpStopBufferPips<=0 || InpMinZonePips<=0 || InpMaxZonePips<InpMinZonePips)return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   high_balance=AccountInfoDouble(ACCOUNT_BALANCE);return INIT_SUCCEEDED;
}

void OnTick()
{
   high_balance=MathMax(high_balance,AccountInfoDouble(ACCOUNT_BALANCE));
   // Run the native engine two years earlier to populate complete zone history,
   // but prohibit all orders during that indicator-only warm-up.
   if(TimeCurrent()<InpTradingFrom)return;
   datetime bar=iTime(_Symbol,PERIOD_M15,0);
   if(bar==0 || bar==last_m15)return;last_m15=bar;
   datetime daily=iTime(_Symbol,PERIOD_D1,0);
   if(daily!=last_daily)
   {
      if(!BuildZones(daily)){ExpertRemove();return;}
      last_daily=daily;
   }
   double before=iClose(_Symbol,PERIOD_M15,2),close=iClose(_Symbol,PERIOD_M15,1);
   if(before<=0 || close<=0)return;
   for(int z=0;z<ArraySize(zones);z++)
   {
      if(close<zones[z].low || close>zones[z].high)continue;
      int direction=before>zones[z].high?1:(before<zones[z].low?-1:0);
      if(direction==0)continue;signals++;
      if(HavePosition()){occupied++;return;}
      MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
      double entry=direction>0?tick.ask:tick.bid;
      double stop=RoundPrice(direction>0?zones[z].low-InpStopBufferPips*Pip():zones[z].high+InpStopBufferPips*Pip());
      double distance=direction>0?entry-stop:stop-entry;
      double target=RoundPrice(entry+direction*InpRewardRisk*distance);
      double guard=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
      bool valid=direction>0?(stop<tick.bid-guard && target>tick.bid+guard):(stop>tick.ask+guard && target<tick.ask-guard);
      if(distance<=0 || !valid){invalid++;return;}
      ENUM_ORDER_TYPE side=direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
      double lots=LotsForRisk(side,entry,stop);
      if(lots<=0){small++;return;}
      bool success=direction>0?trade.Buy(lots,_Symbol,0,stop,target,"D1zone M15 buy") : trade.Sell(lots,_Symbol,0,stop,target,"D1zone M15 sell");
      if(success && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL))placed++;
      else {rejected++;Print("ZONE_ORDER_REJECTED ",trade.ResultRetcodeDescription());}
      return;
   }
}

void OnDeinit(const int reason)
{
   Print("ZONE_STATS rebuilds=",rebuilds," signals=",signals," placed=",placed," rejected=",rejected," undersize_or_margin=",small," invalid_geometry=",invalid," occupied=",occupied," high_balance=",DoubleToString(high_balance,2));
}

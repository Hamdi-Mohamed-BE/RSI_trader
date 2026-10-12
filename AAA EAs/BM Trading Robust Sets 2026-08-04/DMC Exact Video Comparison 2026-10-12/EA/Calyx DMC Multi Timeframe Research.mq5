#property strict
#property version "1.00"
#property description "Research-only mechanical reconstruction of t9Bssop4uqo; not the creator's exact system."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;
input long InpMagic=1210267001;
input int InpPivotStrength=2;
input int InpWeeklyBars=52;
input int InpDailyBars=90;
input int InpH4Bars=180;
input int InpH1Bars=120;
input int InpM15Bars=128;
input int InpATRPeriod=14;
input double InpStopBufferATR=0.10;
input double InpBreakEvenR=0.50;
input double InpMinimumRoomR=0.25;
input int InpRetestExpiryBars=8;
input bool InpTrendRejections=true;
input bool InpHigherTimeframeScalps=true;
input bool InpBreakRetests=true;

struct Zone {
   datetime origin;
   int timeframe;
   int kind; // +1 demand/body-low pivot, -1 supply/body-high pivot
   double lo;
   double hi;
};
struct UsedZone { Zone zone; int direction; bool used; };
Zone g_zones[];
UsedZone g_used[];
CTrade g_trade;
datetime g_bar=0;
int g_atr=INVALID_HANDLE;
int g_setup_dir=0,g_setup_age=0;
Zone g_setup;
ulong g_position=0;
double g_initial_risk=0.0;
long g_counts[3];

double BH(const MqlRates &bar) { return MathMax(bar.open,bar.close); }
double BL(const MqlRates &bar) { return MathMin(bar.open,bar.close); }
bool Pivot(MqlRates &bars[],int i,int kind,int strength) {
   double v=(kind>0 ? BL(bars[i]) : BH(bars[i]));
   for(int j=1;j<=strength;j++) {
      double a=(kind>0 ? BL(bars[i-j]) : BH(bars[i-j]));
      double b=(kind>0 ? BL(bars[i+j]) : BH(bars[i+j]));
      if(kind>0 ? (v>=a || v>=b) : (v<=a || v<=b)) return false;
   }
   return true;
}
bool Same(const Zone &a,const Zone &b) {
   return a.origin==b.origin && a.timeframe==b.timeframe && a.kind==b.kind;
}
bool Available(const Zone &zone,int direction) {
   for(int i=0;i<ArraySize(g_used);i++)
      if(Same(zone,g_used[i].zone) && direction==g_used[i].direction) return !g_used[i].used;
   return true;
}
void Use(const Zone &zone,int direction) {
   for(int i=0;i<ArraySize(g_used);i++) {
      if(Same(zone,g_used[i].zone) && direction==g_used[i].direction) {g_used[i].used=true;return;}
   }
   int n=ArraySize(g_used);ArrayResize(g_used,n+1);
   g_used[n].zone=zone;g_used[n].direction=direction;g_used[n].used=true;
}
void Rearm(double close) {
   for(int i=0;i<ArraySize(g_used);i++) {
      if(g_used[i].used && (g_used[i].direction>0 ? close<g_used[i].zone.lo : close>g_used[i].zone.hi))
         g_used[i].used=false;
   }
}
int Load(ENUM_TIMEFRAMES tf,int count,MqlRates &bars[]) {
   ArraySetAsSeries(bars,true);
   return CopyRates(_Symbol,tf,0,count,bars);
}
int Trend(MqlRates &bars[],int count) {
   int state=0,s=InpPivotStrength;
   double high=0,low=0;
   // Walk forwards in time. A pivot becomes usable only after s CLOSED bars
   // on its right. In a series array index 0 is never used for confirmation.
   for(int k=count-2*s-1;k>=1;k--) {
      int candidate=k+s;
      if(Pivot(bars,candidate,-1,s)) high=BH(bars[candidate]);
      if(Pivot(bars,candidate,1,s)) low=BL(bars[candidate]);
      if(high>0 && bars[k].close>high && bars[k+1].close<=high) state=1;
      else if(low>0 && bars[k].close<low && bars[k+1].close>=low) state=-1;
   }
   return state;
}
void AppendZones(ENUM_TIMEFRAMES tf,MqlRates &bars[],int count) {
   int s=InpPivotStrength;
   for(int i=s+1;i<count-s;i++) {
      for(int kind=-1;kind<=1;kind+=2) {
         if(!Pivot(bars,i,kind,s)) continue;
         int n=ArraySize(g_zones);ArrayResize(g_zones,n+1);
         g_zones[n].origin=bars[i].time;g_zones[n].timeframe=(int)tf;
         g_zones[n].kind=kind;g_zones[n].lo=BL(bars[i]);g_zones[n].hi=BH(bars[i]);
      }
   }
}
bool LatestPivot(MqlRates &bars[],int count,int kind,Zone &zone) {
   int s=InpPivotStrength;
   for(int i=s+1;i<count-s;i++) {
      if(!Pivot(bars,i,kind,s)) continue;
      zone.origin=bars[i].time;zone.timeframe=(int)PERIOD_M15;
      zone.kind=kind;zone.lo=BL(bars[i]);zone.hi=BH(bars[i]);return true;
   }
   return false;
}
double Target(int direction,double entry) {
   double best=0;
   for(int i=0;i<ArraySize(g_zones);i++) {
      double level=(g_zones[i].kind>0 ? g_zones[i].lo : g_zones[i].hi);
      if(direction>0 && level>entry && (best==0 || level<best)) best=level;
      if(direction<0 && level<entry && (best==0 || level>best)) best=level;
   }
   return best;
}
bool Entry(int direction,const Zone &zone,double stop,int module) {
   if(!Available(zone,direction)) return false;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)) return false;
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double entry=(direction>0 ? q.ask : q.bid);
   double target=Target(direction,entry);
   if(tick<=0 || target<=0) return false;
   stop=MathRound(stop/tick)*tick;target=MathRound(target/tick)*tick;
   double risk=direction*(entry-stop),reward=direction*(target-entry);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(risk<=0 || reward<=0 || risk<minimum || reward<minimum || reward/risk<InpMinimumRoomR) return false;
   double result=0;
   if(!OrderCalcProfit(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,_Symbol,1,entry,stop,result) || result>=0) return false;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/(-result);
   lots=MathFloor((MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-12)/step)*step;
   if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)) return false;
   lots=NormalizeDouble(lots,8);
   string labels[3]={"DMC trend rejection","DMC HTF scalp","DMC break retest"};
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0,stop,target,labels[module]) : g_trade.Sell(lots,_Symbol,0,stop,target,labels[module]));
   if(!sent) {Print("ENTRY_REJECT ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());return false;}
   Use(zone,direction);g_initial_risk=risk;
   if(PositionSelect(_Symbol)) {
      g_position=(ulong)PositionGetInteger(POSITION_TICKET);
      g_initial_risk=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
   }
   g_counts[module]++;
   PrintFormat("DMC_ENTRY module=%d dir=%d zone_tf=%d origin=%s risk=%.5f targetR=%.4f",module,direction,zone.timeframe,TimeToString(zone.origin),g_initial_risk,reward/risk);
   return true;
}
bool Manage() {
   if(!PositionSelect(_Symbol) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) {g_position=0;g_initial_risk=0;return false;}
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),stop=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
   int direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
   if(g_initial_risk<=0) g_initial_risk=MathAbs(entry-stop);
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)) return true;
   double price=(direction>0 ? q.bid : q.ask);
   if(g_initial_risk>0 && direction*(price-entry)>=InpBreakEvenR*g_initial_risk && direction*(entry-stop)>0) {
      double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
      if(direction*(price-entry)>minimum) g_trade.PositionModify((ulong)PositionGetInteger(POSITION_TICKET),entry,tp);
   }
   return true;
}
int OnInit() {
   // Hard research-only gate: this build cannot run on a live/demo chart.
   if(!(bool)MQLInfoInteger(MQL_TESTER)) {Print("RESEARCH_ONLY: Strategy Tester required");return INIT_FAILED;}
   if(InpPivotStrength<1 || InpPivotStrength>5 || InpRiskPercent<=0 || InpBreakEvenR<=0 || InpMinimumRoomR<=0) return INIT_PARAMETERS_INCORRECT;
   g_atr=iATR(_Symbol,PERIOD_M15,InpATRPeriod);
   if(g_atr==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);g_trade.SetTypeFillingBySymbol(_Symbol);g_trade.SetDeviationInPoints(20);
   Print("DMC_RECONSTRUCTION_FIXED: closed body pivots, all sessions, nearest mapped target, no optimisation");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) {
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
   PrintFormat("DMC_MODULE_COUNTS trend=%d scalp=%d retest=%d",g_counts[0],g_counts[1],g_counts[2]);
}
void OnTick() {
   bool holding=Manage();
   datetime current=iTime(_Symbol,PERIOD_M15,0);
   if(current==0 || current==g_bar) return;
   g_bar=current;
   MqlRates m[],h[],h4[],d[],w[];
   int nm=Load(PERIOD_M15,InpM15Bars,m),nh=Load(PERIOD_H1,InpH1Bars,h),nh4=Load(PERIOD_H4,InpH4Bars,h4),nd=Load(PERIOD_D1,InpDailyBars,d),nw=Load(PERIOD_W1,InpWeeklyBars,w);
   int required=2*InpPivotStrength+4;
   if(nm<required || nh<required || nh4<required || nd<required || nw<required) return;
   double values[1];if(CopyBuffer(g_atr,0,1,1,values)!=1 || values[0]<=0) return;
   double atr=values[0],buffer=InpStopBufferATR*atr;
   Rearm(m[1].close);
   ArrayResize(g_zones,0);
   AppendZones(PERIOD_W1,w,nw);AppendZones(PERIOD_D1,d,nd);AppendZones(PERIOD_H4,h4,nh4);AppendZones(PERIOD_H1,h,nh);
   if(holding) {g_setup_dir=0;return;}
   if(g_setup_dir!=0) {
      g_setup_age++;
      bool retest=(g_setup_dir>0 ? m[1].low<=g_setup.hi && m[1].close>g_setup.hi && m[1].close>m[1].open : m[1].high>=g_setup.lo && m[1].close<g_setup.lo && m[1].close<m[1].open);
      bool failed=(g_setup_dir>0 ? m[1].close<g_setup.lo : m[1].close>g_setup.hi);
      if(retest && InpBreakRetests) {
         double stop=(g_setup_dir>0 ? MathMin(g_setup.lo,m[1].low)-buffer : MathMax(g_setup.hi,m[1].high)+buffer);
         if(Entry(g_setup_dir,g_setup,stop,2)) {g_setup_dir=0;return;}
      }
      if(failed || g_setup_age>InpRetestExpiryBars) g_setup_dir=0;
   }
   int daily=Trend(d,nd),hourly=Trend(h,nh);
   for(int module=0;module<2;module++) {
      if(module==0 && !InpTrendRejections) continue;
      if(module==1 && !InpHigherTimeframeScalps) continue;
      for(int i=0;i<ArraySize(g_zones);i++) {
         Zone z=g_zones[i];
         if(module==0 && z.timeframe!=(int)PERIOD_H1) continue;
         if(module==1 && z.timeframe==(int)PERIOD_H1) continue;
         int dir=z.kind;
         if(module==0 && (daily!=dir || hourly!=dir)) continue;
         bool reaction=(dir>0 ? m[1].low<=z.hi && m[1].high>=z.lo && m[1].close>z.hi && m[1].close>m[1].open : m[1].high>=z.lo && m[1].low<=z.hi && m[1].close<z.lo && m[1].close<m[1].open);
         if(!reaction) continue;
         double stop=(dir>0 ? MathMin(z.lo,m[1].low)-buffer : MathMax(z.hi,m[1].high)+buffer);
         if(Entry(dir,z,stop,module)) {g_setup_dir=0;return;}
      }
   }
   if(InpBreakRetests) {
      Zone z;
      if(LatestPivot(m,nm,-1,z) && m[1].close>z.hi && m[2].close<=z.hi) {g_setup=z;g_setup_dir=1;g_setup_age=0;}
      else if(LatestPivot(m,nm,1,z) && m[1].close<z.lo && m[2].close>=z.lo) {g_setup=z;g_setup_dir=-1;g_setup_age=0;}
   }
}

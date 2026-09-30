#ifndef CALYX_EXIT_RESEARCH
#define CALYX_EXIT_RESEARCH
#include <Trade/Trade.mqh>
// Research-only replacement exits. Entry signals, initial stops and time exits remain native.
input int InpEMMode=0; // 0=native, 1=fixed R, 2=M15 ATR, 3=previous-session profile ladder
input double InpEMTargetR=0.75;
input double InpEMActivateR=1.0;
input double InpEMATRMultiple=2.0;
input string InpEMTag="research";
CTrade em_trade;
int em_atr=INVALID_HANDLE;
ulong em_ticket[64];
double em_initial[64],em_best[64];
datetime em_open[64],em_bar=0,em_profile_day=0;
double em_levels[5];
int em_level_count=0,em_modifies=0,em_rejects=0;

double EM_Price(const string symbol,const double p) {
 double step=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
 return NormalizeDouble(MathRound(p/step)*step,(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
}
double EM_Target(const string symbol,const int side,double price,const double sl,const double tp) {
 if(InpEMMode==0)return tp;
 if(InpEMMode!=1)return 0.0;
 if(price<=0){MqlTick q;if(!SymbolInfoTick(symbol,q))return tp;price=side>0?q.ask:q.bid;}
 return EM_Price(symbol,price+side*InpEMTargetR*MathAbs(price-sl));
}
// Keep the original CTrade instance's magic/fill/deviation configuration.
class EMTrade: public CTrade {
public:
 bool Buy(const double v,const string s=NULL,double p=0,const double sl=0,const double tp=0,const string c="") {
  string sym=s==NULL?_Symbol:s;return CTrade::Buy(v,s,p,sl,EM_Target(sym,1,p,sl,tp),c);
 }
 bool Sell(const double v,const string s=NULL,double p=0,const double sl=0,const double tp=0,const string c="") {
  string sym=s==NULL?_Symbol:s;return CTrade::Sell(v,s,p,sl,EM_Target(sym,-1,p,sl,tp),c);
 }
 bool BuyStop(const double v,const double p,const string s=NULL,const double sl=0,const double tp=0,
              const ENUM_ORDER_TYPE_TIME t=ORDER_TIME_GTC,const datetime e=0,const string c="") {
  string sym=s==NULL?_Symbol:s;return CTrade::BuyStop(v,p,s,sl,EM_Target(sym,1,p,sl,tp),t,e,c);
 }
 bool SellStop(const double v,const double p,const string s=NULL,const double sl=0,const double tp=0,
               const ENUM_ORDER_TYPE_TIME t=ORDER_TIME_GTC,const datetime e=0,const string c="") {
  string sym=s==NULL?_Symbol:s;return CTrade::SellStop(v,p,s,sl,EM_Target(sym,-1,p,sl,tp),t,e,c);
 }
 bool PositionModify(const ulong t,const double s,const double p) {
  if(InpEMMode>0)return true;return CTrade::PositionModify(t,s,p);
 }
 bool PositionModify(const string t,const double s,const double p) {
  if(InpEMMode>0)return true;return CTrade::PositionModify(t,s,p);
 }
};
bool EM_Init() {
 if(!MQLInfoInteger(MQL_TESTER))return false;
 ArrayInitialize(em_ticket,0);ArrayInitialize(em_initial,0);ArrayInitialize(em_best,0);
 em_atr=iATR(_Symbol,PERIOD_M15,14);
 em_trade.SetTypeFillingBySymbol(_Symbol);em_trade.SetDeviationInPoints(50);
 return em_atr!=INVALID_HANDLE && InpEMMode>=0 && InpEMMode<=3;
}
void EM_Profile(const datetime now) {
 datetime day=(datetime)(((long)now/86400)*86400);
 if(em_profile_day==day)return;em_profile_day=day;em_level_count=0;
 // Previous completed UTC trading day with >=300 M1 bars; skip weekends/empty days.
 MqlRates r[];int n=0;
 for(int back=1;back<=7;back++) {
  datetime start=day-back*86400;
  n=CopyRates(_Symbol,PERIOD_M1,start,start+86400-1,r);
  if(n>=300)break;
 }
 if(n<300)return;
 double em_lo=DBL_MAX,em_hi=-DBL_MAX;
 for(int i=0;i<n;i++){em_lo=MathMin(em_lo,r[i].low);em_hi=MathMax(em_hi,r[i].high);}
 if(em_hi<=em_lo)return;
 double bins[64];ArrayInitialize(bins,0);double total=0,width=(em_hi-em_lo)/64;
 for(int i=0;i<n;i++) {
  int b=(int)MathFloor(((r[i].high+r[i].low+r[i].close)/3-em_lo)/width);
  b=MathMax(0,MathMin(63,b));bins[b]+=(double)r[i].tick_volume;total+=(double)r[i].tick_volume;
 }
 if(total<=0)return;
 int em_poc=0;for(int i=1;i<64;i++)if(bins[i]>bins[em_poc])em_poc=i;
 int left=em_poc,right=em_poc;double covered=bins[em_poc];
 while(covered<0.70*total && (left>0 || right<63)) {
  double a=left>0?bins[left-1]:-1,b=right<63?bins[right+1]:-1;
  if(b>=a && right<63){right++;covered+=bins[right];}else{left--;covered+=bins[left];}
 }
 em_levels[0]=em_lo;em_levels[1]=em_lo+left*width;em_levels[2]=em_lo+(em_poc+0.5)*width;
 em_levels[3]=em_lo+(right+1)*width;em_levels[4]=em_hi;em_level_count=5;
}
void EM_Run() {
 if(InpEMMode<2)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 bool any=false;
 for(int i=PositionsTotal()-1;i>=0;i--) {
  ulong t=PositionGetTicket(i);if(!t || PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
  any=true;int index=-1;
  for(int j=0;j<64;j++)if(em_ticket[j]==t){index=j;break;}
  if(index<0) {
   for(int j=0;j<64;j++)if(em_ticket[j]==0 || !PositionSelectByTicket(em_ticket[j])){index=j;break;}
   if(index<0 || !PositionSelectByTicket(t))continue;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL);
   em_ticket[index]=t;em_initial[index]=MathAbs(entry-sl);em_best[index]=entry;
   em_open[index]=(datetime)PositionGetInteger(POSITION_TIME);
  }
 }
 if(!any)return;
 datetime bar=iTime(_Symbol,PERIOD_M15,0);if(bar==0 || bar==em_bar)return;em_bar=bar;
 MqlRates closed[];double atr[];
 if(CopyRates(_Symbol,PERIOD_M15,1,1,closed)!=1 || CopyBuffer(em_atr,0,1,1,atr)!=1 || atr[0]<=0)return;
 if(InpEMMode==3)EM_Profile(TimeCurrent());
 for(int j=0;j<64;j++) {
  ulong t=em_ticket[j];if(t==0 || !PositionSelectByTicket(t) || em_initial[j]<=0)continue;
  // Never use a high/low/close preceding the position's entry.
  if(closed[0].time<em_open[j])continue;
  int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
  double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL);
  double price=side>0?q.bid:q.ask,candidate=sl;
  if(side>0)em_best[j]=MathMax(em_best[j],closed[0].close);else em_best[j]=MathMin(em_best[j],closed[0].close);
  if(side*(em_best[j]-entry)<InpEMActivateR*em_initial[j])continue;
  if(InpEMMode==2)candidate=em_best[j]-side*InpEMATRMultiple*atr[0];
  else {
   double buffer=0.2*atr[0];
   for(int k=0;k<em_level_count;k++) {
    if(side*(em_levels[k]-entry)<=0 || side*(closed[0].close-em_levels[k])<buffer)continue;
    double level=em_levels[k]-side*buffer;
    if(side*(level-candidate)>0)candidate=level;
   }
  }
  candidate=EM_Price(_Symbol,candidate);
  double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
  if(side*(candidate-sl)<_Point || side*(price-candidate)<=gap+_Point)continue;
  if(em_trade.PositionModify(t,candidate,0))em_modifies++;else em_rejects++;
 }
}
void EM_End() {
 if(em_atr!=INVALID_HANDLE)IndicatorRelease(em_atr);
 PrintFormat("EM_SUMMARY|mode=%d|mods=%d|rejects=%d",InpEMMode,em_modifies,em_rejects);
}
#endif

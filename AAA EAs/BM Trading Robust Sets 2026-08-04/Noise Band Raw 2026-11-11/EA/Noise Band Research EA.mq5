#property strict
#property version "1.00"
#property description "Research only (2026-11-11). Noise Band intraday momentum (Zarattini/Aziz/Barbon 2024; QuantLab simplified band): from 10:00 to 15:00 New York, on closed M30"
#property description "candles, trade when |close - 09:30 open| > k*sqrt(K)*ATR14(M30). Stop s*ATR, trail 2*ATR after +1R, flat 16:00 NY, one trade a day. RULES.md."
#include <Trade/Trade.mqh>

input double InpK=1.4;                   // band width (paper 0.6, QuantLab wider 1.4)
input double InpStopATR=2.0;             // initial stop in ATR (paper 1.5)
input double InpTrailATR=2.0;            // trailing distance in ATR
input double InpTrailStartR=1.0;         // trail once the trade is this many R in profit
input int    InpATRPeriod=14;
input double InpRiskPercent=1.0;         // % of balance, lots rounded UP to the step
input bool   InpRandomDirection=false;   // control: random direction, same distances
input int    InpSeed=1;
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpDeviationPoints=50;
input long   InpMagic=2911120;

CTrade g_trade; int g_atr=INVALID_HANDLE; datetime g_last_bar=0; int g_day=0; bool g_traded=false;
double g_risk=0.0,g_trail=0.0,g_best=0.0; long g_signals=0,g_entries=0,g_flat=0;

datetime NthSunday(int y,int m,int n){MqlDateTime t={};t.year=y;t.mon=m;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
bool NyDst(datetime utc){MqlDateTime d;TimeToStruct(utc,d);return utc>=NthSunday(d.year,3,2)+7*3600&&utc<NthSunday(d.year,11,1)+6*3600;}
int SrvOff(){if((bool)MQLInfoInteger(MQL_TESTER))return InpServerUtcOffsetHours*3600;datetime s=TimeTradeServer(),u=TimeGMT();if(s<=0||u<=0)return InpServerUtcOffsetHours*3600;return (int)MathRound((double)(s-u)/1800.0)*1800;}
datetime NyTime(datetime server){datetime utc=server-SrvOff();return utc-(NyDst(utc)?4:5)*3600;}
int NyMinute(datetime server){MqlDateTime n;TimeToStruct(NyTime(server),n);return n.hour*60+n.min;}
int NyKey(datetime server){MqlDateTime n;TimeToStruct(NyTime(server),n);return n.year*10000+n.mon*100+n.day;}
int NyDow(datetime server){MqlDateTime n;TimeToStruct(NyTime(server),n);return n.day_of_week;}

bool HasPos(ulong &ticket){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;return true;}}
   return false;
}
double Lots(ENUM_ORDER_TYPE type,double entry,double stop){
   double one=0.0; if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one)||MathAbs(one)<=0.0) return 0.0;
   double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   return MathMax(mn,MathMin(mx,MathCeil((MathMin(raw,mx)-1e-12)/st)*st));
}
void CloseAll(){ulong t;while(HasPos(t)){if(!g_trade.PositionClose(t,InpDeviationPoints))break;}}

void Manage(){
   ulong t; if(!HasPos(t)||g_risk<=0.0) return;
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   int dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1); double op=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL);
   double px=(dir>0?k.bid:k.ask); g_best=(dir>0?MathMax(g_best,px):MathMin(g_best,px));
   if((g_best-op)*dir<InpTrailStartR*g_risk) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS); double want=NormalizeDouble(g_best-dir*g_trail,dg);
   if((dir>0&&want>sl+_Point*0.5&&want<k.bid)||(dir<0&&want<sl-_Point*0.5&&want>k.ask)) g_trade.PositionModify(t,want,0.0);
}

void OnBar(){
   datetime t1=iTime(_Symbol,PERIOD_M30,1); if(t1<=0) return;
   int dow=NyDow(t1); if(dow<1||dow>5) return;
   int key=NyKey(t1); if(key!=g_day){g_day=key;g_traded=false;}
   int close_min=NyMinute(t1)+30; if(close_min<600||close_min>900||(close_min-570)%30!=0||g_traded) return;
   ulong tk; if(HasPos(tk)) return;
   // the 09:30 New York bar of today
   int s930=-1; for(int i=1;i<=24;i++){datetime bt=iTime(_Symbol,PERIOD_M30,i);if(bt<=0)break;if(NyKey(bt)!=key)break;if(NyMinute(bt)==570){s930=i;break;}}
   if(s930<0) return;
   double open930=iOpen(_Symbol,PERIOD_M30,s930),c=iClose(_Symbol,PERIOD_M30,1),atr[1];
   if(CopyBuffer(g_atr,0,1,1,atr)!=1||atr[0]<=0.0) return;
   int K=(close_min-570)/30; double thr=InpK*MathSqrt((double)K)*atr[0],mv=c-open930; int dir=0;
   if(mv>thr) dir=1; else if(mv<-thr) dir=-1; if(dir==0) return;
   g_signals++; g_traded=true;
   if(InpRandomDirection) dir=((MathRand()&1)==1?1:-1);
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS); double e=(dir>0?k.ask:k.bid),stop=NormalizeDouble(e-dir*InpStopATR*atr[0],dg);
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,stop); if(v<=0.0) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0.0,stop,0.0,"NB"):g_trade.Sell(v,_Symbol,0.0,stop,0.0,"NB"));
   if(ok){g_entries++;g_risk=InpStopATR*atr[0];g_trail=InpTrailATR*atr[0];g_best=e;PrintFormat("NB_ENTRY %s K=%d move=%.2f thr=%.2f atr=%.2f lots=%.2f",dir>0?"buy":"sell",K,mv,thr,atr[0],v);}
}

int OnInit(){
   if(InpK<=0||InpStopATR<=0||InpTrailATR<=0||InpRiskPercent<=0) return INIT_PARAMETERS_INCORRECT;
   g_atr=iATR(_Symbol,PERIOD_M30,InpATRPeriod); if(g_atr==INVALID_HANDLE) return INIT_FAILED;
   MathSrand(InpSeed); g_last_bar=iTime(_Symbol,PERIOD_M30,0);
   PrintFormat("NB_SPEC k=%.2f stop=%.2f trail=%.2f start=%.2f random=%d",InpK,InpStopATR,InpTrailATR,InpTrailStartR,InpRandomDirection);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r){if(g_atr!=INVALID_HANDLE)IndicatorRelease(g_atr);PrintFormat("NB_SUMMARY signals=%I64d entries=%I64d flat_closes=%I64d",g_signals,g_entries,g_flat);}
void OnTick(){
   datetime now=TimeCurrent(); ulong t;
   if(HasPos(t)&&NyMinute(now)>=960&&NyDow(now)>=1&&NyDow(now)<=5){CloseAll();g_flat++;}
   Manage();
   datetime b0=iTime(_Symbol,PERIOD_M30,0); if(b0>0&&b0!=g_last_bar){g_last_bar=b0;OnBar();}
}

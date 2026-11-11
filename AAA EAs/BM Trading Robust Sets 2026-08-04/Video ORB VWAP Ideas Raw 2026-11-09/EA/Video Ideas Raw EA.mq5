#property copyright "Calyx research: raw rules from two Matteo Conti interviews and one reel (PLAN.md, frozen 2026-11-09)"
#property version   "1.00"
#property strict
// RESEARCH ONLY. Never attach to a live chart. Times are New York; the broker server clock is UTC (InpServerUtcOffsetHours).

#include <Trade/Trade.mqh>

input int    InpStrategy=1;          // 1 DRIFT, 2 VAULT, 3 VWAPADX, 4 ONB, 5 REEL
input bool   InpUseBias=true;        // ONB / REEL: overnight thirds bias (false = first break either way)
input bool   InpRandomDirection=false;
input int    InpSeed=1;
input double InpRiskPercent=1.0;
input int    InpServerUtcOffsetHours=0;
input long   InpMagic=91109001;
input int    InpDeviationPoints=50;

CTrade g_trade;
datetime g_last_bar=0;
int g_day=0,g_trades=0,g_losses=0;
bool g_had_pos=false;
// DRIFT
int g_trend=0; bool g_armed=false;
// VAULT
double g_open01=0.0,g_barrier=0.0;
// VWAPADX
double g_orh=0.0,g_orl=0.0; bool g_or_armed=false,g_touched=false;
// ONB / REEL
int g_bias=0; double g_onh=0.0,g_onl=0.0; bool g_setup=false,g_done=false;
int g_adx=INVALID_HANDLE;

ENUM_TIMEFRAMES ChartTF()
  {
   if(InpStrategy==1) return PERIOD_M5;
   if(InpStrategy==2) return PERIOD_M30;
   if(InpStrategy==3) return PERIOD_M1;
   return PERIOD_M15;
  }

//------------------------------------------------------------------ New York clock
datetime MakeUtc(const int y,const int m,const int d,const int h)
  {
   MqlDateTime v; ZeroMemory(v); v.year=y; v.mon=m; v.day=d; v.hour=h; return StructToTime(v);
  }
int NthSunday(const int y,const int m,const int n)
  {
   MqlDateTime f; TimeToStruct(MakeUtc(y,m,1,0),f); return 1+((7-f.day_of_week)%7)+(n-1)*7;
  }
int NyOffset(const datetime utc)
  {
   MqlDateTime p; TimeToStruct(utc,p);
   datetime a=MakeUtc(p.year,3,NthSunday(p.year,3,2),7),b=MakeUtc(p.year,11,NthSunday(p.year,11,1),6);
   return (utc>=a && utc<b ? -4 : -5);
  }
datetime ToNy(const datetime server)
  {
   datetime utc=server-InpServerUtcOffsetHours*3600; return utc+NyOffset(utc)*3600;
  }
datetime NyToServer(const datetime ny)
  {
   int off=NyOffset(ny+5*3600); return ny-off*3600+InpServerUtcOffsetHours*3600;
  }
int NyMinute(const datetime server) { MqlDateTime s; TimeToStruct(ToNy(server),s); return s.hour*60+s.min; }
int NyDow(const datetime server) { MqlDateTime s; TimeToStruct(ToNy(server),s); return s.day_of_week; }
int NyKey(const datetime server) { MqlDateTime s; TimeToStruct(ToNy(server),s); return s.year*10000+s.mon*100+s.day; }
datetime TodayNy(const datetime server,const int minute)   // server time of today's New York clock time
  {
   MqlDateTime s; TimeToStruct(ToNy(server),s); s.hour=minute/60; s.min=minute%60; s.sec=0; return NyToServer(StructToTime(s));
  }

//------------------------------------------------------------------ helpers
bool HasPos()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
     }
   return false;
  }
void CloseAll()
  {
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         if(!g_trade.PositionClose(t)) Print("VIDEO close failed: ",g_trade.ResultRetcodeDescription());
     }
  }
double LastClosedNet()
  {
   if(!HistorySelect(TimeCurrent()-3*86400,TimeCurrent()+60)) return 0.0;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
     {
      ulong d=HistoryDealGetTicket(i);
      if(d==0 || HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic) continue;
      long e=HistoryDealGetInteger(d,DEAL_ENTRY);
      if(e==DEAL_ENTRY_OUT || e==DEAL_ENTRY_OUT_BY)
         return HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION);
     }
   return 0.0;
  }
double Lots(const ENUM_ORDER_TYPE type,const double entry,const double stop)
  {
   double one=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one) || MathAbs(one)<=0.0) return 0.0;
   double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<=0.0 || st<=0.0) return 0.0;
   double v=MathCeil((MathMin(raw,mx)-1e-12)/st)*st;
   return MathMax(mn,MathMin(mx,v));
  }
int Direction(const int rule)
  {
   if(!InpRandomDirection) return rule;
   return ((MathRand()&1)==1 ? 1 : -1);
  }
bool Enter(const int dir,const double stop_dist,const double target_dist,const string tag)
  {
   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || stop_dist<=0.0 || target_dist<=0.0) return false;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*stop_dist,dg),tp=NormalizeDouble(e+dir*target_dist,dg);
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,sl);
   if(v<=0.0) { Print("VIDEO skipped: no valid volume"); return false; }
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0.0,sl,tp,tag):g_trade.Sell(v,_Symbol,0.0,sl,tp,tag));
   if(ok) { g_trades++; g_had_pos=true; }
   else Print("VIDEO order rejected: ",g_trade.ResultRetcodeDescription());
   return ok;
  }
// VWAP of the closed bars of tf from anchor (server time) up to and including bar shift 'last'
double Vwap(const ENUM_TIMEFRAMES tf,const datetime anchor,const int last)
  {
   MqlRates r[]; ArraySetAsSeries(r,true);
   int n=CopyRates(_Symbol,tf,0,600,r); if(n<=last) return 0.0;
   double pv=0.0,vv=0.0;
   for(int i=n-1;i>=last;i--)
     {
      if(r[i].time<anchor) continue;
      double w=(double)MathMax((long)1,r[i].tick_volume); pv+=(r[i].high+r[i].low+r[i].close)/3.0*w; vv+=w;
     }
   return (vv>0.0?pv/vv:0.0);
  }
// mean of the last 15 completed D1 true ranges (true_range=true) or high-low ranges
double DailyAverage(const bool true_range)
  {
   MqlRates d[]; ArraySetAsSeries(d,true);
   if(CopyRates(_Symbol,PERIOD_D1,1,16,d)!=16) return 0.0;
   double s=0.0;
   for(int i=0;i<15;i++)
     {
      double hi=d[i].high,lo=d[i].low;
      if(true_range) { hi=MathMax(hi,d[i+1].close); lo=MathMin(lo,d[i+1].close); }
      s+=hi-lo;
     }
   return s/15.0;
  }
double AdxValue(const int shift)
  {
   double b[1]; if(g_adx==INVALID_HANDLE || CopyBuffer(g_adx,0,shift,1,b)!=1) return -1.0; return b[0];
  }

//------------------------------------------------------------------ strategies (called once per new chart bar; bar 1 just closed)
void NewDay(const int key)
  {
   g_day=key; g_trades=0; g_losses=0; g_trend=0; g_armed=false; g_open01=0.0; g_barrier=0.0;
   g_orh=0.0; g_orl=0.0; g_or_armed=false; g_touched=false; g_bias=0; g_setup=false; g_done=false;
  }

void Drift(const datetime t1,const int close_min)
  {
   if(close_min%15==0 && close_min>=600)                                  // a 15-minute bar closed (from 10:00 so two VWAP points exist)
     {
      datetime anchor=TodayNy(t1,570);
      double v1=Vwap(PERIOD_M15,anchor,1),v0=Vwap(PERIOD_M15,anchor,2),c1=iClose(_Symbol,PERIOD_M15,1),c5=iClose(_Symbol,PERIOD_M15,5);
      int trend=0;
      if(v1>0.0 && v0>0.0 && c5>0.0)
        {
         if(c1>v1 && v1>v0 && c1>=c5*1.001) trend=1;
         else if(c1<v1 && v1<v0 && c1<=c5*0.999) trend=-1;
        }
      if(trend!=g_trend) { g_trend=trend; g_armed=(trend!=0); }
     }
   if(close_min<630 || close_min>930 || g_trend==0 || !g_armed || HasPos() || g_trades>=4 || g_losses>=2) return;
   double o=iOpen(_Symbol,PERIOD_M5,1),c=iClose(_Symbol,PERIOD_M5,1);
   if((g_trend>0 && c<o) || (g_trend<0 && c>o))
     {
      int dir=Direction(g_trend);
      if(Enter(dir,80.0,dir>0?40.0:50.0,"DRIFT")) g_armed=false;
     }
  }

void Vault(const datetime t1,const int close_min)
  {
   if(g_open01<=0.0)
     {
      datetime a=TodayNy(t1,60); int s=iBarShift(_Symbol,PERIOD_M30,a,true);
      if(s>=0 && close_min>60) { double atr=DailyAverage(true); g_open01=iOpen(_Symbol,PERIOD_M30,s); g_barrier=(atr>0.0?g_open01+0.30*atr:0.0); }
     }
   if(g_barrier<=0.0 || close_min<660 || close_min>900 || HasPos() || g_trades>=3) return;
   double c=iClose(_Symbol,PERIOD_M30,1),v=Vwap(PERIOD_M30,TodayNy(t1,60),1);
   if(v>0.0 && c>g_barrier && c>v) Enter(1,75.0,40.0,"VAULT");
  }

void VwapAdx(const datetime t1,const int close_min)
  {
   if(close_min==600 && g_orh<=0.0)
     {
      int s=iBarShift(_Symbol,PERIOD_M1,TodayNy(t1,570),true); if(s<1) return;
      g_orh=iHigh(_Symbol,PERIOD_M1,iHighest(_Symbol,PERIOD_M1,MODE_HIGH,s,1)); g_orl=iLow(_Symbol,PERIOD_M1,iLowest(_Symbol,PERIOD_M1,MODE_LOW,s,1));
      return;
     }
   if(g_orh<=0.0 || close_min<=600 || close_min>930) return;
   double c=iClose(_Symbol,PERIOD_M1,1),l=iLow(_Symbol,PERIOD_M1,1),v=Vwap(PERIOD_M1,TodayNy(t1,570),1);
   if(v<=0.0) return;
   if(!g_or_armed) { if(c>g_orh) g_or_armed=true; return; }
   if(HasPos()) return;
   if(l<=v) g_touched=true;
   if(!g_touched || c<=v) return;
   double a1=AdxValue(1),a2=AdxValue(2);
   if(a1<=20.0 || a2<0.0 || a1>a2) return;                                 // ADX above 20 and not rising: otherwise wait
   double tp=iHigh(_Symbol,PERIOD_M1,iHighest(_Symbol,PERIOD_M1,MODE_HIGH,5,1)),sl=iLow(_Symbol,PERIOD_M1,iLowest(_Symbol,PERIOD_M1,MODE_LOW,20,1));
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   g_touched=false;                                                        // a new touch is needed after this signal
   if(tp<=k.ask || sl>=k.bid) { Print("VIDEO VWAPADX skipped: target not above entry or stop not below"); return; }
   Enter(1,k.ask-sl,tp-k.ask,"VWAPADX");
  }

void Onb(const datetime t1,const int close_min,const bool adx,const bool true_range)
  {
   if(!g_setup && close_min>=585)                                          // 09:45: the 09:30 bar has closed
     {
      g_setup=true;
      int so=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,570),true),sn=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,0),false);
      if(so<1 || sn<=so) { g_done=true; return; }
      g_onh=iHigh(_Symbol,PERIOD_M15,iHighest(_Symbol,PERIOD_M15,MODE_HIGH,sn-so,so+1)); g_onl=iLow(_Symbol,PERIOD_M15,iLowest(_Symbol,PERIOD_M15,MODE_LOW,sn-so,so+1));
      g_orh=iHigh(_Symbol,PERIOD_M15,so); g_orl=iLow(_Symbol,PERIOD_M15,so);
      double op=iOpen(_Symbol,PERIOD_M15,so),rg=g_onh-g_onl;
      if(rg<=0.0) { g_done=true; return; }
      g_bias=(op>=g_onl+rg*2.0/3.0 ? 1 : (op<=g_onl+rg/3.0 ? -1 : 0));
      if(InpUseBias && g_bias==0) g_done=true;
      return;
     }
   if(!g_setup || g_done || close_min<600 || close_min>915 || HasPos()) return;
   double c=iClose(_Symbol,PERIOD_M15,1); int rule=0;
   if(c>g_orh && (!InpUseBias || g_bias>0)) rule=1;
   else if(c<g_orl && (!InpUseBias || g_bias<0)) rule=-1;
   if(rule==0) return;
   if(adx && AdxValue(1)<=20.0) return;
   double base=DailyAverage(true_range); if(base<=0.0) return;
   g_done=true;
   Enter(Direction(rule),0.30*base,0.90*base,(InpStrategy==4?"ONB":"REEL"));
  }

//------------------------------------------------------------------ events
int OnInit()
  {
   if(InpStrategy<1 || InpStrategy>5 || InpRiskPercent<=0.0) return INIT_PARAMETERS_INCORRECT;
   if(InpStrategy==3) g_adx=iADX(_Symbol,PERIOD_M1,14);
   if(InpStrategy==4) g_adx=iADX(_Symbol,PERIOD_M15,14);
   if((InpStrategy==3 || InpStrategy==4) && g_adx==INVALID_HANDLE) return INIT_FAILED;
   MathSrand(InpSeed); g_last_bar=iTime(_Symbol,ChartTF(),0);
   PrintFormat("VIDEO_SPEC strategy=%d bias=%d random=%d risk=%.2f tf=%s",InpStrategy,InpUseBias,InpRandomDirection,InpRiskPercent,EnumToString(ChartTF()));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { if(g_adx!=INVALID_HANDLE) IndicatorRelease(g_adx); }

void OnTick()
  {
   datetime now=TimeCurrent();
   if(g_had_pos && !HasPos()) { g_had_pos=false; if(LastClosedNet()<0.0) g_losses++; if(InpStrategy==1 && g_trend!=0) g_armed=true; }
   int mn=NyMinute(now),dow=NyDow(now);
   int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : 930);
   if(HasPos() && dow>=1 && dow<=5 && mn>=flat) CloseAll();
   ENUM_TIMEFRAMES tf=ChartTF(); datetime b0=iTime(_Symbol,tf,0);
   if(b0<=0 || b0==g_last_bar) return;
   g_last_bar=b0;
   datetime t1=iTime(_Symbol,tf,1); if(t1<=0) return;
   if(NyDow(t1)<1 || NyDow(t1)>5) return;
   int key=NyKey(t1); if(key!=g_day) NewDay(key);
   int close_min=NyMinute(t1)+PeriodSeconds(tf)/60;                      // New York minute at which bar 1 closed
   if(InpStrategy==1) Drift(t1,close_min);
   else if(InpStrategy==2) Vault(t1,close_min);
   else if(InpStrategy==3) VwapAdx(t1,close_min);
   else if(InpStrategy==4) Onb(t1,close_min,true,true);
   else Onb(t1,close_min,false,false);
  }

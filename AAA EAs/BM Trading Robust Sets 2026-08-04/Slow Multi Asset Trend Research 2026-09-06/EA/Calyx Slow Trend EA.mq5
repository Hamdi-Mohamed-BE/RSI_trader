#property strict
#property version   "1.20"
#property description "Calyx slow time-series momentum EA for the locked XAUUSD portfolio configuration."

#include <Trade/Trade.mqh>
#include "..\..\_Shared\CalyxAdaptivePortfolio.mqh"

input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H4;
input int InpHorizonMode=3;             // 0=1m, 1=3m, 2=6m, 3=1/3/6m, 4=3/6/12m
input int InpTrendMode=1;               // 0=none, 1=EMA100, 2=EMA200, 3=EMA200+rising
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input int InpSessionMinuteUTC=-1;       // -1=first available, 60=Asia, 480=London, 810=NY, 840=overlap
input int InpStopMode=0;                // 0=ATR, 1=recent swing, 2=chandelier boundary
input double InpStopATR=1.5;
input int InpExitMode=1;                // 0=signal reversal, 1=fixed RR, 2=adaptive RR, 3=time
input double InpRewardRisk=6.0;
input int InpMaximumHoldDays=0;
input int InpManagement=0;              // 0=none, 1=BE, 2=ATR trail, 3=chandelier trail, 4=M15 50-to-20
input double InpRiskPercent=1.0;
input bool InpAdaptivePortfolioControls=false;
input int InpMaximumDeviationPoints=100;
input ulong InpMagic=969060311;
input bool InpTesterOnly=false;

CTrade trade;
int atrHandle=INVALID_HANDLE;
int emaHandle=INVALID_HANDLE;
datetime lastM15=0;
datetime lastSignalStamp=0;
datetime lastEntryTime=0;
double initialRiskDistance=0.0;

int ScaleBars(const int trading_days)
{
   if(InpSignalTimeframe==PERIOD_H4) return MathMax(1,trading_days*6);
   if(InpSignalTimeframe==PERIOD_W1) return MathMax(1,(int)MathRound(trading_days*52.0/252.0));
   return MathMax(1,trading_days);
}

int EmaLength()
{
   if(InpTrendMode==1) return ScaleBars(100);
   if(InpTrendMode>=2) return ScaleBars(200);
   return 0;
}

bool ReadBufferValue(const int handle,const int shift,double &value)
{
   double a[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,a)!=1) return false;
   value=a[0]; return MathIsValidNumber(value);
}

int SignOf(const double x)
{
   if(x>0.0) return 1;
   if(x<0.0) return -1;
   return 0;
}

bool MomentumSignal(int &direction,double &strength,datetime &stamp)
{
   stamp=iTime(_Symbol,InpSignalTimeframe,1);
   const double current=iClose(_Symbol,InpSignalTimeframe,1);
   if(stamp<=0 || current<=0.0) return false;
   int horizons[3]; int count=0;
   if(InpHorizonMode==0) { horizons[0]=21; count=1; }
   else if(InpHorizonMode==1) { horizons[0]=63; count=1; }
   else if(InpHorizonMode==2) { horizons[0]=126; count=1; }
   else if(InpHorizonMode==3) { horizons[0]=21; horizons[1]=63; horizons[2]=126; count=3; }
   else { horizons[0]=63; horizons[1]=126; horizons[2]=252; count=3; }
   double vote=0.0;
   for(int i=0;i<count;i++)
   {
      const double past=iClose(_Symbol,InpSignalTimeframe,1+ScaleBars(horizons[i]));
      if(past<=0.0) return false;
      vote+=(double)SignOf(current/past-1.0);
   }
   vote/=count; direction=SignOf(vote); strength=MathAbs(vote);
   if(direction==0) return true;
   if(InpTrendMode>0)
   {
      double emaNow=0.0;
      if(!ReadBufferValue(emaHandle,1,emaNow)) return false;
      if((direction>0 && current<=emaNow)||(direction<0 && current>=emaNow)) direction=0;
      if(direction!=0 && InpTrendMode==3)
      {
         double emaOld=0.0;
         if(!ReadBufferValue(emaHandle,1+ScaleBars(21),emaOld)) return false;
         if((direction>0 && emaNow<=emaOld)||(direction<0 && emaNow>=emaOld)) direction=0;
      }
   }
   if(direction>0 && !InpAllowLong) direction=0;
   if(direction<0 && !InpAllowShort) direction=0;
   return true;
}

bool OurPosition(ulong &ticket,int &side,double &entry,double &sl,double &tp,datetime &opened)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      const ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1;
      entry=PositionGetDouble(POSITION_PRICE_OPEN); sl=PositionGetDouble(POSITION_SL); tp=PositionGetDouble(POSITION_TP);
      opened=(datetime)PositionGetInteger(POSITION_TIME);
      return true;
   }
   return false;
}

double CurrentATR()
{
   double x=0.0; return ReadBufferValue(atrHandle,1,x) ? x : 0.0;
}

bool Boundaries(double &swingLow,double &swingHigh,double &chandLong,double &chandShort)
{
   const int look=ScaleBars(10),chandLook=MathMax(5,ScaleBars(20));
   swingLow=DBL_MAX;swingHigh=-DBL_MAX;double rollHigh=-DBL_MAX,rollLow=DBL_MAX;
   for(int i=1;i<=MathMax(look,chandLook);i++)
   {
      const double lo=iLow(_Symbol,InpSignalTimeframe,i),hi=iHigh(_Symbol,InpSignalTimeframe,i);
      if(lo<=0.0||hi<=0.0) return false;
      if(i<=look){swingLow=MathMin(swingLow,lo);swingHigh=MathMax(swingHigh,hi);}
      if(i<=chandLook){rollLow=MathMin(rollLow,lo);rollHigh=MathMax(rollHigh,hi);}
   }
   const double atr=CurrentATR(); if(atr<=0.0) return false;
   chandLong=rollHigh-3.0*atr;chandShort=rollLow+3.0*atr;return true;
}

double VolumeForRisk(const int side,const double entry,const double stop)
{
   double loss=0.0;
   const ENUM_ORDER_TYPE kind=side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcProfit(kind,_Symbol,1.0,entry,stop,loss) || loss==0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,(long)InpMagic);
   if(adaptive<=0.0) return 0.0;
   const double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent*adaptive/100.0;
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0.0 || minimum<=0.0 || maximum<=0.0) return 0.0;
   const double oneLotLoss=MathAbs(loss),requested=cash/oneLotLoss;
   double volume=MathCeil((MathMin(requested,maximum)-1e-12)/step)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   if(volume>requested+1e-12)
      PrintFormat("Slow Trend risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk %.2f exceeds target %.2f.",requested,volume,oneLotLoss*volume,cash);
   return volume;
}

void RestoreLastEntryTime()
{
   // Broker deal history survives terminal/VPS restarts, unlike a RAM-only
   // timestamp.  Rebuild the cooldown state before evaluating new signals.
   const datetime now=TimeCurrent();
   const datetime from=now-30*86400;
   if(!HistorySelect(from,now)) return;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      const ulong deal=HistoryDealGetTicket(index);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if((ulong)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      const ENUM_DEAL_ENTRY entryType=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entryType!=DEAL_ENTRY_IN && entryType!=DEAL_ENTRY_INOUT) continue;
      lastEntryTime=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      return;
   }
}

bool SessionAllowed()
{
   if(InpSessionMinuteUTC<0) return true;
   MqlDateTime d;TimeToStruct(TimeCurrent(),d);
   return d.hour*60+d.min==InpSessionMinuteUTC;
}

void CloseIfRequired(const int signal)
{
   ulong ticket;int side;double entry,sl,tp;datetime opened;
   if(!OurPosition(ticket,side,entry,sl,tp,opened)) return;
   if(InpExitMode==0 && (signal==0 || signal==-side)) trade.PositionClose(ticket);
   else if(InpMaximumHoldDays>0 && TimeCurrent()-opened>=InpMaximumHoldDays*86400) trade.PositionClose(ticket);
}

void ManageOnM15Close()
{
   ulong ticket;int side;double entry,sl,tp;datetime opened;
   if(!OurPosition(ticket,side,entry,sl,tp,opened) || initialRiskDistance<=0.0 || InpManagement==0) return;
   const double close=iClose(_Symbol,PERIOD_M15,1);
   const double ask=close+SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double progress=side>0 ? (close-entry)/initialRiskDistance : (entry-ask)/initialRiskDistance;
   double candidate=sl;
   if(InpManagement==1 && progress>=1.0) candidate=entry;
   else if(InpManagement==2 && progress>=1.0)
   {
      const double atr=CurrentATR();candidate=side>0 ? close-2.5*atr : ask+2.5*atr;
   }
   else if(InpManagement==3 && progress>=1.0)
   {
      double a,b,longLine,shortLine;if(!Boundaries(a,b,longLine,shortLine)) return;
      candidate=side>0 ? MathMin(longLine,close) : MathMax(shortLine,ask);
   }
   else if(InpManagement==4 && progress>=0.5) candidate=entry+side*0.2*initialRiskDistance;
   else return;
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   candidate=NormalizeDouble(candidate,digits);
   if((side>0 && (sl==0.0||candidate>sl))||(side<0 && (sl==0.0||candidate<sl))) trade.PositionModify(ticket,candidate,tp);
}

void TryEntry(const int signal,const double strength,const datetime stamp)
{
   if(signal==0 || !SessionAllowed() || stamp<=lastSignalStamp) return;
   ulong t;int existing;double a,b,c;datetime d;if(OurPosition(t,existing,a,b,c,d)) return;
   const int cooldown=InpSignalTimeframe==PERIOD_W1 ? 7*86400 : 86400;
   if(lastEntryTime>0 && TimeCurrent()-lastEntryTime<cooldown) return;
   const double atr=CurrentATR();if(atr<=0.0) return;
   const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID),ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double entry=signal>0?ask:bid;double dist=InpStopATR*atr;
   double swingLow,swingHigh,chandLong,chandShort;
   if(!Boundaries(swingLow,swingHigh,chandLong,chandShort)) return;
   if(InpStopMode==1)
   {
      const double raw=signal>0?entry-swingLow:swingHigh-entry;
      dist=MathMax(.75*atr,MathMin(5.0*atr,raw+.15*atr));
   }
   else if(InpStopMode==2)
   {
      const double raw=signal>0?entry-chandLong:chandShort-entry;
      dist=MathMax(.75*atr,MathMin(5.0*atr,raw));
   }
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double stop=NormalizeDouble(entry-signal*dist,digits),rr=InpRewardRisk;
   if(InpExitMode==2) rr=strength>=.99?4.0:1.5;
   double target=(InpExitMode==1||InpExitMode==2)?NormalizeDouble(entry+signal*rr*dist,digits):0.0;
   const double volume=VolumeForRisk(signal,entry,stop);if(volume<=0.0) return;
   bool ok=signal>0?trade.Buy(volume,_Symbol,0.0,stop,target,"Calyx slow trend"):trade.Sell(volume,_Symbol,0.0,stop,target,"Calyx slow trend");
   if(ok){initialRiskDistance=dist;lastEntryTime=TimeCurrent();lastSignalStamp=stamp;}
}

int OnInit()
{
   if(InpTesterOnly && !MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   if(InpRiskPercent<=0.0 || InpRiskPercent>10.0) return INIT_PARAMETERS_INCORRECT;
   atrHandle=iATR(_Symbol,InpSignalTimeframe,14);if(atrHandle==INVALID_HANDLE) return INIT_FAILED;
   const int ema=EmaLength();if(ema>0){emaHandle=iMA(_Symbol,InpSignalTimeframe,ema,0,MODE_EMA,PRICE_CLOSE);if(emaHandle==INVALID_HANDLE)return INIT_FAILED;}
   trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(InpMaximumDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   RestoreLastEntryTime();
   // A live attach or terminal restart must wait for the next completed signal
   // candle instead of entering late on a signal that formed before startup.
   if(!MQLInfoInteger(MQL_TESTER)) lastSignalStamp=iTime(_Symbol,InpSignalTimeframe,1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(atrHandle!=INVALID_HANDLE) IndicatorRelease(atrHandle);
   if(emaHandle!=INVALID_HANDLE) IndicatorRelease(emaHandle);
}

void OnTick()
{
   const datetime m15=iTime(_Symbol,PERIOD_M15,0);
   if(m15!=lastM15){lastM15=m15;ManageOnM15Close();}
   int signal=0;double strength=0.0;datetime stamp=0;if(!MomentumSignal(signal,strength,stamp)) return;
   CloseIfRequired(signal);
   TryEntry(signal,strength,stamp);
}

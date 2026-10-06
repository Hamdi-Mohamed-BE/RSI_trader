#property strict
#property version   "1.20"
#property description "Calyx slow time-series momentum EA for the locked XAUUSD portfolio configuration."

#include <Trade/Trade.mqh>
#include "CalyxAdaptivePortfolio.mqh"

input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H4;
input int InpHorizonMode=3;             // 0=1m, 1=3m, 2=6m, 3=1/3/6m, 4=3/6/12m
input int InpTrendMode=1;               // 0=none, 1=EMA100, 2=EMA200, 3=EMA200+rising
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input int InpSessionMinuteUTC=-1;       // -1=first available, 60=Asia, 480=London, 810=NY, 840=overlap
input int InpStopMode=0;                // 0=ATR, 1=recent swing, 2=chandelier boundary
input double InpStopATR=1.5;
input int InpExitMode=1;                // 0=signal reversal, 1=fixed RR, 2=adaptive RR, 3=time
input double InpRewardRisk=1;
input int InpMaximumHoldDays=0;
input int InpManagement=0;              // 0=none, 1=BE, 2=ATR trail, 3=chandelier trail, 4=M15 50-to-20
input double InpRiskPercent=1.0;
input bool InpAdaptivePortfolioControls=false;
input int InpMaximumDeviationPoints=100;
input ulong InpMagic=969060311;
input bool InpTesterOnly=false;
// Research-only inputs. Defaults preserve the shipped normal/FTMO signals.
input string InpAuditTag="SMOKE";
input bool InpResearchConfirmCandle=false;
input double InpResearchVoteMin=0.0;
input int InpResearchSession=0; // 0 all, 1 00-08, 2 07-12, 3 13-21, 4 13-16 broker clock
input int InpResearchSkipDays=0; // 1 Monday, 2 Friday, 3 both
input double InpResearchADXMin=0.0;
input bool InpResearchDI=false;
input int InpResearchCooldownDays=0; // 0 original auto; otherwise fixed days
input double InpResearchStopPercent=0.5;
input double InpResearchStopPrice=20.0;
input double InpResearchTriggerR=0.0; // 0 retains original mode-specific trigger
input double InpResearchTrailATR=2.5;
input double InpResearchTrailPercent=0.25;
input double InpResearchLockR=0.2;
input bool InpResearchBrokerGuard=false;

int auditEvents=INVALID_HANDLE,auditEquity=INVALID_HANDLE,adxHandle=INVALID_HANDLE;
int auditEntries=0,auditPartials=0,auditBE=0,auditMinPartials=0;
int auditOrderFailed=0,auditCloseFailed=0,auditModifyFailed=0;
ulong auditPosition=0;
bool auditPartialDone=false,auditBEDone=false;
double auditBudget=0.0,auditPeak=0.0,auditMaxDD=0.0,auditCashDD=0.0;
datetime auditLastTrace=0;

string AuditPrefix(){return "CalyxSlowOptimize20261005\\"+InpAuditTag;}
void AuditEvent(const string event,const ulong id,const int side,const double entry,const double sl,const double tp,const double requested=0.0,const double actual=0.0,const string note="")
{
   FileWrite(auditEvents,(long)TimeCurrent(),event,id,side,entry,sl,tp,requested,actual,0,0,0,0,0,0,0,0,0,0,note);
}
void AuditTrace(const bool force=false)
{
   const double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   auditPeak=MathMax(auditPeak,eq);
   if(auditPeak>0){auditMaxDD=MathMax(auditMaxDD,100.0*(auditPeak-eq)/auditPeak);auditCashDD=MathMax(auditCashDD,auditPeak-eq);}
   if(force || TimeCurrent()-auditLastTrace>=300)
   {
      FileWrite(auditEquity,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),eq,auditMaxDD,auditCashDD);
      auditLastTrace=TimeCurrent();
   }
}
void AuditEntry(const int side,const double stop,const double target)
{
   ulong ticket=0;int direction=0;double px=0,sl=0,tp=0;datetime opened=0;
   if(!OurPosition(ticket,direction,px,sl,tp,opened) || !PositionSelectByTicket(ticket)){Print("SLOW_AUDIT_MISSING_POSITION");return;}
   auditPosition=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   double risk=0.0,volume=PositionGetDouble(POSITION_VOLUME);
   if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,volume,px,stop,risk)){Print("SLOW_AUDIT_RISK_FAILED");return;}
   auditEntries++;auditPartialDone=false;auditBEDone=false;
   AuditEvent("entry",auditPosition,side,px,stop,target,auditBudget,MathAbs(risk),"volume="+DoubleToString(volume,8)+"|signal="+(string)(long)lastSignalStamp);
}
bool ResearchEntryAllowed(const int direction,const double strength)
{
   if(InpResearchVoteMin>0 && strength<InpResearchVoteMin)return false;
   MqlDateTime d;TimeToStruct(TimeCurrent(),d);
   if((InpResearchSkipDays==1||InpResearchSkipDays==3) && d.day_of_week==1)return false;
   if((InpResearchSkipDays==2||InpResearchSkipDays==3) && d.day_of_week==5)return false;
   int h=d.hour;
   if(InpResearchSession==1 && (h<0||h>=8))return false;
   if(InpResearchSession==2 && (h<7||h>=12))return false;
   if(InpResearchSession==3 && (h<13||h>=21))return false;
   if(InpResearchSession==4 && (h<13||h>=16))return false;
   if(InpResearchConfirmCandle)
   {
      double close=iClose(_Symbol,InpSignalTimeframe,1),open=iOpen(_Symbol,InpSignalTimeframe,1);
      if(direction*(close-open)<=0)return false;
   }
   if(InpResearchADXMin>0 || InpResearchDI)
   {
      double adx=0,plus=0,minus=0;
      if(!ReadBufferValue(adxHandle,1,adx))return false;
      double p[1],m[1];
      if(CopyBuffer(adxHandle,1,1,1,p)!=1 || CopyBuffer(adxHandle,2,1,1,m)!=1)return false;
      plus=p[0];minus=m[0];
      if(adx<InpResearchADXMin)return false;
      if(InpResearchDI && (direction>0?plus<=minus:minus<=plus))return false;
   }
   return true;
}

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
   bool required=(InpExitMode==0 && (signal==0 || signal==-side)) || (InpMaximumHoldDays>0 && TimeCurrent()-opened>=InpMaximumHoldDays*86400);
   if(required)
   {
      bool ok=trade.PositionClose(ticket);
      if(!ok || trade.ResultRetcode()!=TRADE_RETCODE_DONE){auditCloseFailed++;AuditEvent("close_failed",auditPosition,side,entry,sl,tp,0,0,trade.ResultRetcodeDescription());}
   }
}

void ManageOnM15Close()
{
   ulong ticket;int side;double entry,sl,tp;datetime opened;
   if(!OurPosition(ticket,side,entry,sl,tp,opened) || initialRiskDistance<=0.0 || InpManagement==0) return;
   const double close=iClose(_Symbol,PERIOD_M15,1);
   const double ask=close+SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double progress=side>0 ? (close-entry)/initialRiskDistance : (entry-ask)/initialRiskDistance;
   double candidate=sl;
   const double trigger=InpResearchTriggerR>0?InpResearchTriggerR:(InpManagement==4?0.5:1.0);
   if(InpManagement==1 && progress>=trigger) candidate=entry;
   else if(InpManagement==2 && progress>=trigger)
   {
      const double atr=CurrentATR();candidate=side>0 ? close-InpResearchTrailATR*atr : ask+InpResearchTrailATR*atr;
   }
   else if(InpManagement==3 && progress>=trigger)
   {
      double a,b,longLine,shortLine;if(!Boundaries(a,b,longLine,shortLine)) return;
      candidate=side>0 ? MathMin(longLine,close) : MathMax(shortLine,ask);
   }
   else if(InpManagement==4 && progress>=trigger) candidate=entry+side*InpResearchLockR*initialRiskDistance;
   else if(InpManagement==5 && progress>=trigger)candidate=side>0?close*(1.0-InpResearchTrailPercent/100.0):ask*(1.0+InpResearchTrailPercent/100.0);
   else if(InpManagement==6 && progress>=trigger)
   {
      candidate=entry;
      if(!auditPartialDone && PositionSelectByTicket(ticket))
      {
         double volume=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
         double half=NormalizeDouble(MathFloor((volume*0.5+1e-10)/step)*step,8);
         if(half>=minimum-1e-9 && volume-half>=minimum-1e-9)
         {
            bool ok=trade.PositionClosePartial(ticket,half);
            if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE){auditPartialDone=true;auditPartials++;AuditEvent("partial",auditPosition,side,entry,sl,tp,half,0,"half-at-R");}
            else{auditCloseFailed++;AuditEvent("partial_failed",auditPosition,side,entry,sl,tp,half,0,trade.ResultRetcodeDescription());return;}
         }
         else{auditPartialDone=true;auditMinPartials++;AuditEvent("partial_minlot_skip",auditPosition,side,entry,sl,tp,volume,0,"minimum-lot");}
      }
   }
   else return;
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   candidate=NormalizeDouble(candidate,digits);
   if((side>0 && (sl==0.0||candidate>sl))||(side<0 && (sl==0.0||candidate<sl)))
   {
      if(InpResearchBrokerGuard)
      {
         const double quote=SymbolInfoDouble(_Symbol,side>0?SYMBOL_BID:SYMBOL_ASK),point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
         const double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point+2*point;
         if(side*(quote-candidate)<=gap)return;
      }
      bool ok=trade.PositionModify(ticket,candidate,tp);
      if(ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_NO_CHANGES))
      {
         if(!auditBEDone && side*(candidate-entry)>=0){auditBEDone=true;auditBE++;AuditEvent("breakeven",auditPosition,side,entry,candidate,tp,0,0,"entry-or-better");}
      }
      else{auditModifyFailed++;AuditEvent("modify_failed",auditPosition,side,entry,candidate,tp,0,0,trade.ResultRetcodeDescription());}
   }
}

void TryEntry(const int signal,const double strength,const datetime stamp)
{
   if(signal==0 || !SessionAllowed() || stamp<=lastSignalStamp) return;
   if(!ResearchEntryAllowed(signal,strength))return;
   ulong t;int existing;double a,b,c;datetime d;if(OurPosition(t,existing,a,b,c,d)) return;
   const int cooldown=InpResearchCooldownDays>0?InpResearchCooldownDays*86400:(InpSignalTimeframe==PERIOD_W1 ? 7*86400 : 86400);
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
   else if(InpStopMode==3)dist=entry*InpResearchStopPercent/100.0;
   else if(InpStopMode==4)dist=InpResearchStopPrice;
   else if(InpStopMode==5)
   {
      const double raw=signal>0?entry-iLow(_Symbol,InpSignalTimeframe,1):iHigh(_Symbol,InpSignalTimeframe,1)-entry;
      dist=MathMax(.75*atr,MathMin(5.0*atr,raw+.15*atr));
   }
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double stop=NormalizeDouble(entry-signal*dist,digits),rr=InpRewardRisk;
   if(InpExitMode==2) rr=strength>=.99?4.0:1.5;
   double target=(InpExitMode==1||InpExitMode==2)?NormalizeDouble(entry+signal*rr*dist,digits):0.0;
   const double volume=VolumeForRisk(signal,entry,stop);if(volume<=0.0) return;
   auditBudget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   bool ok=signal>0?trade.Buy(volume,_Symbol,0.0,stop,target,"Calyx slow trend"):trade.Sell(volume,_Symbol,0.0,stop,target,"Calyx slow trend");
   if(ok){initialRiskDistance=dist;lastEntryTime=TimeCurrent();lastSignalStamp=stamp;}
   if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE)AuditEntry(signal,stop,target);
   else{auditOrderFailed++;AuditEvent("order_failed",0,signal,entry,stop,target,0,0,trade.ResultRetcodeDescription());}
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || InpAdaptivePortfolioControls) return INIT_FAILED;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   if(InpRiskPercent<=0.0 || InpRiskPercent>10.0) return INIT_PARAMETERS_INCORRECT;
   auditEvents=FileOpen(AuditPrefix()+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   auditEquity=FileOpen(AuditPrefix()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(auditEvents<0||auditEquity<0)return INIT_FAILED;
   FileWrite(auditEvents,"epoch","event","position_id","dir","entry","sl","tp","requested_risk","actual_risk","pd_from","pd_to","val","poc","vah","vwap","dev_poc","signal_epoch","body_fraction","close_location","note");
   FileWrite(auditEquity,"epoch","balance","equity","max_dd_pct","max_dd_cash");
   auditPeak=AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpResearchADXMin>0 || InpResearchDI){adxHandle=iADX(_Symbol,InpSignalTimeframe,14);if(adxHandle==INVALID_HANDLE)return INIT_FAILED;}
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
   if(adxHandle!=INVALID_HANDLE) IndicatorRelease(adxHandle);
   if(auditEvents>=0)FileClose(auditEvents);
   if(auditEquity>=0)FileClose(auditEquity);
}

void OnTick()
{
   AuditTrace();
   const datetime m15=iTime(_Symbol,PERIOD_M15,0);
   if(m15!=lastM15){lastM15=m15;ManageOnM15Close();}
   int signal=0;double strength=0.0;datetime stamp=0;if(!MomentumSignal(signal,strength,stamp)) return;
   CloseIfRequired(signal);
   TryEntry(signal,strength,stamp);
}

double OnTester()
{
   AuditTrace(true);
   int f=FileOpen(AuditPrefix()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   FileWrite(f,"deal","epoch","position_id","entry","type","reason","volume","price","gross","commission","swap","fee","comment");
   HistorySelect(0,D'2099.01.01');
   ulong owned[];
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong t=HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(t,DEAL_TYPE)>1 || HistoryDealGetInteger(t,DEAL_ENTRY)!=DEAL_ENTRY_IN || HistoryDealGetInteger(t,DEAL_MAGIC)!=InpMagic)continue;
      int n=ArraySize(owned);ArrayResize(owned,n+1);owned[n]=(ulong)HistoryDealGetInteger(t,DEAL_POSITION_ID);
   }
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong t=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(t,DEAL_TYPE);
      if(type>1)continue;
      bool ours=false;for(int j=0;j<ArraySize(owned);j++)if(owned[j]==(ulong)HistoryDealGetInteger(t,DEAL_POSITION_ID)){ours=true;break;}
      if(!ours)continue;
      FileWrite(f,t,HistoryDealGetInteger(t,DEAL_TIME),HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_ENTRY),type,
         HistoryDealGetInteger(t,DEAL_REASON),HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),
         HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
   }
   FileClose(f);FileFlush(auditEvents);FileFlush(auditEquity);
   PrintFormat("FLOW_SUMMARY entries=%d partials=%d be=%d minpartial=%d orders_failed=%d close_failed=%d modify_failed=%d maxdd=%.8f cashdd=%.8f",auditEntries,auditPartials,auditBE,auditMinPartials,auditOrderFailed,auditCloseFailed,auditModifyFailed,auditMaxDD,auditCashDD);
   return TesterStatistics(STAT_PROFIT);
}

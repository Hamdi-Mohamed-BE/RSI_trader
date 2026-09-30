// Research-only extensions. Case arrays are baked into a separate, hashed build per batch.
// Base case must pass exact raw parity before any search is permitted.
input int InpCase=0;
double OptProfileHigh=0,OptProfileLow=0;
bool OptEnter(const int direction,const double stop,const string comment);
bool OptExposureFull();
#include "RawCore.mqh"

int OEntry=0,OStop=0,OTrail=0,OExit=0,OSession=0,ODirection=0,OFilter=0,ODay=0;
int OMaxDay=0,OMaxPositions=1,OReentry=1,OMaxBars=0,OHoldWeekend=1;
double OStopParam=2,OStart=1,ODistance=1.5;
int OHma=INVALID_HANDLE,OHhtf=INVALID_HANDLE,OHadx=INVALID_HANDLE;
datetime OLastManagementBar=0;
struct O_TRACK { ulong ticket; double risk; bool partial; };
O_TRACK OTrack[];
int OConfirmation=0;
double OConfirmStop=0,OConfirmHigh=0,OConfirmLow=0;
datetime OConfirmAfter=0,OConfirmExpiry=0;

int OCountPositions()
{
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) n++;
   return n;
}
bool OptExposureFull() { return OCountPositions()>=OMaxPositions || AAA_HasOrder(_Symbol,InpMagic) || OConfirmation!=0; }

int ONthSunday(int year,int month,int nth)
{
   MqlDateTime d={}; d.year=year; d.mon=month; d.day=1;
   datetime t=StructToTime(d); TimeToStruct(t,d);
   return 1+(7-d.day_of_week)%7+7*(nth-1);
}
bool OUSDst(datetime utc)
{
   MqlDateTime d; TimeToStruct(utc,d);
   MqlDateTime begin={}; begin.year=d.year; begin.mon=3; begin.day=ONthSunday(d.year,3,2); begin.hour=7;
   MqlDateTime end={}; end.year=d.year; end.mon=11; end.day=ONthSunday(d.year,11,1); end.hour=6;
   return utc>=StructToTime(begin) && utc<StructToTime(end);
}
bool OInSession()
{
   if(OSession==0) return true;
   MqlDateTime d; TimeToStruct(TimeCurrent(),d); // Exness research binding is UTC
   int m=d.hour*60+d.min,ny=m+(OUSDst(TimeCurrent()) ? -240 : -300);
   if(OSession==1) return m>=0 && m<480;
   if(OSession==2) return m>=420 && m<960;
   if(OSession==3) return ny>=570 && ny<960;
   if(OSession==4) return m>=720 && m<960;
   if(OSession==5) return ny>=570 && ny<660;
   return false;
}
bool OEntryAllowed(const int direction)
{
   if(ODirection==1 && direction<0) return false;
   if(ODirection==2 && direction>0) return false;
   if(!OInSession()) return false;
   MqlDateTime d; TimeToStruct(TimeCurrent(),d);
   if((ODay==1 || ODay==3) && d.day_of_week==1) return false;
   if((ODay==2 || ODay==3) && d.day_of_week==5) return false;
   if(OMaxDay>0 || OReentry==0)
   {
      d.hour=0; d.min=0; d.sec=0;
      if(!HistorySelect(StructToTime(d),TimeCurrent())) return false;
      int entries=0; bool lost=false;
      for(int i=0;i<HistoryDealsTotal();i++)
      {
         ulong t=HistoryDealGetTicket(i);
         if(HistoryDealGetString(t,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(t,DEAL_MAGIC)!=InpMagic) continue;
         if(HistoryDealGetInteger(t,DEAL_ENTRY)==DEAL_ENTRY_IN) entries++;
         if(HistoryDealGetInteger(t,DEAL_ENTRY)==DEAL_ENTRY_OUT && HistoryDealGetDouble(t,DEAL_PROFIT)+HistoryDealGetDouble(t,DEAL_SWAP)+HistoryDealGetDouble(t,DEAL_COMMISSION)<0) lost=true;
      }
      if(OMaxDay>0 && entries>=OMaxDay) return false;
      if(OReentry==0 && lost) return false;
   }
   if(OFilter==0) return true;
   double atr=AAA_BufferValue(g_atr,0,1),ma=AAA_BufferValue(OHma,0,1);
   if(OFilter==1) return direction*(ma-AAA_BufferValue(OHma,0,4))>0;
   if(OFilter==2) return direction*(iClose(_Symbol,PERIOD_H1,1)-AAA_BufferValue(OHhtf,0,1))>0;
   if(OFilter==3) return AAA_BufferValue(OHadx,0,1)>=20;
   if(OFilter==4) return direction*(AAA_BufferValue(OHadx,1,1)-AAA_BufferValue(OHadx,2,1))>0;
   if(OFilter==5)
   {
      double a[]; int n=CopyBuffer(g_atr,0,2,100,a); if(n!=100) return false;
      int below=0; for(int i=0;i<n;i++) if(a[i]<atr) below++;
      return below>=20 && below<=80;
   }
   if(OFilter==6)
   {
      MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return false;
      return atr>0 && (t.ask-t.bid)<=0.1*atr;
   }
   return false;
}
double OExtreme(const int direction,const int bars)
{
   double out=(direction>0 ? DBL_MAX : -DBL_MAX);
   for(int i=1;i<=bars;i++) out=(direction>0 ? MathMin(out,iLow(_Symbol,InpSignalTimeframe,i)) : MathMax(out,iHigh(_Symbol,InpSignalTimeframe,i)));
   return out;
}
double OTarget(const int direction,const double entry,const double risk)
{
   if(OExit==1) return 0;
   if(OExit!=2) return AAA_Price(_Symbol,entry+direction*risk*InpRewardRisk);
   double levels[5]={g_poc,g_vah,g_val,OptProfileHigh,OptProfileLow},best=DBL_MAX,price=0;
   for(int i=0;i<5;i++)
      if(direction*(levels[i]-entry)>0 && MathAbs(levels[i]-entry)<best) { best=MathAbs(levels[i]-entry); price=levels[i]; }
   return AAA_Price(_Symbol,price);
}
bool OSend(const int direction,const double sl,const string comment,const int entry_mode)
{
   MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return false;
   double atr=AAA_BufferValue(g_atr,0,1),entry=(direction>0 ? t.ask : t.bid);
   if(entry_mode==2) entry-=direction*0.25*atr;
   if(entry_mode==3) entry-=direction*(_Symbol=="XAUUSD" ? 0.5 : 0.01);
   if(entry_mode==4) entry=(direction>0 ? MathMax(t.ask,iHigh(_Symbol,InpSignalTimeframe,1))+(t.ask-t.bid) : MathMin(t.bid,iLow(_Symbol,InpSignalTimeframe,1))-(t.ask-t.bid));
   entry=AAA_Price(_Symbol,entry);
   double stop=AAA_Price(_Symbol,sl),risk=direction*(entry-stop);
   if(risk<=0 || risk<InpMinStopSpreadMultiple*(t.ask-t.bid)) return false;
   if(entry_mode==0 && OExit==0) return AAA_SendMarket(_Symbol,direction,stop,InpRewardRisk,InpRiskPercent,InpMagic,comment);
   double tp=OTarget(direction,entry,risk);
   if(OExit==2 && tp==0) return false;
   double volume=AAA_LotsForRisk(_Symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),entry,stop,InpRiskPercent);
   if(volume<=0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic); AAA_Trade.SetTypeFillingBySymbol(_Symbol); AAA_Trade.SetDeviationInPoints(20);
   if(entry_mode==0) return direction>0 ? AAA_Trade.Buy(volume,_Symbol,0,stop,tp,comment) : AAA_Trade.Sell(volume,_Symbol,0,stop,tp,comment);
   datetime expiry=TimeCurrent()+4*PeriodSeconds(InpSignalTimeframe);
   if(entry_mode==4) return direction>0 ? AAA_Trade.BuyStop(volume,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment) : AAA_Trade.SellStop(volume,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   return direction>0 ? AAA_Trade.BuyLimit(volume,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment) : AAA_Trade.SellLimit(volume,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment);
}
bool OptEnter(const int direction,const double raw_stop,const string comment)
{
   if(!OEntryAllowed(direction) || OptExposureFull()) return false;
   MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return false;
   double atr=AAA_BufferValue(g_atr,0,1),entry=(direction>0 ? t.ask : t.bid),stop=raw_stop;
   if(OStop==1) stop=entry-direction*OStopParam*atr;
   if(OStop==2) stop=entry-direction*entry*OStopParam/100;
   if(OStop==3) stop=entry-direction*OStopParam;
   if(OStop==4) stop=OExtreme(direction,1)-direction*InpStopBufferATR*atr;
   if(OStop==5) stop=OExtreme(direction,5)-direction*InpStopBufferATR*atr;
   if(OEntry==1)
   {
      OConfirmation=direction; OConfirmStop=stop; OConfirmAfter=iTime(_Symbol,InpSignalTimeframe,0);
      OConfirmExpiry=OConfirmAfter+4*PeriodSeconds(InpSignalTimeframe);
      OConfirmHigh=iHigh(_Symbol,InpSignalTimeframe,1); OConfirmLow=iLow(_Symbol,InpSignalTimeframe,1);
      return true;
   }
   return OSend(direction,stop,comment,OEntry);
}
void OManage()
{
   datetime bar=iTime(_Symbol,InpSignalTimeframe,0);
   bool fresh=bar!=OLastManagementBar; OLastManagementBar=bar;
   MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return;
   if(OConfirmation!=0 && fresh && bar>OConfirmAfter)
   {
      int d=OConfirmation;
      double close=iClose(_Symbol,InpSignalTimeframe,1);
      if(TimeCurrent()>=OConfirmExpiry) OConfirmation=0;
      else if((d>0 && close>OConfirmHigh) || (d<0 && close<OConfirmLow))
      { OConfirmation=0; if(OEntryAllowed(d) && !OptExposureFull()) OSend(d,OConfirmStop,"VP confirmed",0); }
   }
   if(OTrail==0 && OExit<3 && OMaxBars==0 && OHoldWeekend==1) return;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      int idx=-1; for(int k=0;k<ArraySize(OTrack);k++) if(OTrack[k].ticket==ticket) { idx=k; break; }
      double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      int direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
      if(idx<0)
      {
         idx=ArraySize(OTrack); ArrayResize(OTrack,idx+1);
         OTrack[idx].ticket=ticket; OTrack[idx].risk=MathAbs(entry-sl); OTrack[idx].partial=false;
      }
      double risk=OTrack[idx].risk,price=direction>0 ? t.bid : t.ask;
      MqlDateTime now; TimeToStruct(TimeCurrent(),now);
      bool timed=(OMaxBars>0 && TimeCurrent()-opened>=OMaxBars*PeriodSeconds(InpSignalTimeframe));
      if(OExit==3 && TimeCurrent()-opened>=24*PeriodSeconds(InpSignalTimeframe)) timed=true;
      if(OExit==4 && ((OSession!=0 && !OInSession()) || (OSession==0 && now.hour*60+now.min>=1315))) timed=true;
      if(OHoldWeekend==0 && now.day_of_week==5 && now.hour*60+now.min>=1255) timed=true;
      if(timed) { AAA_Trade.PositionClose(ticket); continue; }
      if(risk<=0 || direction*(price-entry)<OStart*risk) continue;
      if(OExit==5 && !OTrack[idx].partial && direction*(price-entry)>=risk)
      {
         double v=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
         double part=MathFloor(v*0.5/step)*step;
         if(part>=minimum && v-part>=minimum) { if(AAA_Trade.PositionClosePartial(ticket,part)) OTrack[idx].partial=true; }
         else OTrack[idx].partial=true; // cannot partially close at the broker's minimum lot
      }
      int trail=(OExit==5 && OTrail==0 ? 2 : OTrail);
      if(trail==0) continue;
      double atr=AAA_BufferValue(g_atr,0,1),candidate=sl;
      if(trail==1) candidate=entry;
      if(trail==2) candidate=price-direction*ODistance*atr;
      if(trail==3) candidate=price-direction*price*ODistance/100;
      if(trail==4) { if(!fresh) continue; candidate=AAA_BufferValue(OHma,0,1); }
      if(trail==5) { if(!fresh) continue; candidate=OExtreme(direction,3)-direction*0.1*atr; }
      if(trail==6)
      {
         if(!fresh) continue;
         candidate=OExtreme(-direction,20)-direction*ODistance*atr;
      }
      if(trail==7) candidate=entry+direction*(MathFloor(direction*(price-entry)/risk)-0.8)*risk;
      double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),gap=MathMax(point,(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);
      if(direction*(price-candidate)<gap || direction*(candidate-sl)<=point) continue;
      AAA_Trade.PositionModify(ticket,AAA_Price(_Symbol,candidate),tp);
   }
}
void ApplyCase()
{
   int i=InpCase;
   InpSignalTimeframe=(ENUM_TIMEFRAMES)(int)Cases[i][0]; InpRewardRisk=Cases[i][1];
   InpBins=(int)Cases[i][2]; InpValueAreaPercent=Cases[i][3]; InpATRPeriod=(int)Cases[i][4];
   InpStopBufferATR=Cases[i][5]; InpBreakoutATR=Cases[i][6]; InpPullbackNearATR=Cases[i][7]; InpMaxPullbackDepth=Cases[i][8];
   OEntry=(int)Cases[i][9]; OStop=(int)Cases[i][10]; OStopParam=Cases[i][11];
   OTrail=(int)Cases[i][12]; OStart=Cases[i][13]; ODistance=Cases[i][14]; OExit=(int)Cases[i][15];
   OSession=(int)Cases[i][16]; ODirection=(int)Cases[i][17]; OFilter=(int)Cases[i][18]; ODay=(int)Cases[i][19];
   OMaxDay=(int)Cases[i][20]; OMaxPositions=(int)Cases[i][21]; OReentry=(int)Cases[i][22]; OMaxBars=(int)Cases[i][23]; OHoldWeekend=(int)Cases[i][24];
   InpSetups=(int)Cases[i][25]; InpRiskPercent=1.0; InpAdaptivePortfolioControls=false;
}
int OnInit()
{
   if(!(bool)MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0)) return INIT_PARAMETERS_INCORRECT;
   ApplyCase();
   int rc=CoreOnInit(); if(rc!=INIT_SUCCEEDED) return rc;
   OHma=iMA(_Symbol,InpSignalTimeframe,50,0,MODE_EMA,PRICE_CLOSE);
   OHhtf=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);
   OHadx=iADX(_Symbol,InpSignalTimeframe,14);
   if(OHma==INVALID_HANDLE || OHhtf==INVALID_HANDLE || OHadx==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}
void OnTick() { OManage(); CoreOnTick(); }
void OnDeinit(const int reason) { CoreOnDeinit(reason); IndicatorRelease(OHma); IndicatorRelease(OHhtf); IndicatorRelease(OHadx); }
double OnTester()
{
   double n=TesterStatistics(STAT_TRADES),profit=TesterStatistics(STAT_PROFIT),pf=TesterStatistics(STAT_PROFIT_FACTOR),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(n<60 || profit<=0 || pf<=1) return -1000+MathMin(0,profit/10000);
   return MathMin(pf,3.0)*MathSqrt(n/100.0)*(profit/10000.0)/(0.05+dd/100.0);
}

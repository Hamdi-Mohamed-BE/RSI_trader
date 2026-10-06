// TESTER ONLY. The production EA is not edited or installed.
input int InpFlowMode=0; // 0=exact legacy; 1=new flow; 2=legacy AND flow
input string InpAuditTag="SMOKE";
input int InpOptStopMode=0; // 0=structure; 1=ATR; 2=price percentage
input double InpOptStopFactor=1.0;
input double InpOptStopATR=1.5;
input double InpOptStopPricePct=0.25;
input int InpOptManage=0; // 0=legacy; 1=BE; 2=ATR trail; 3=half at1R + BE
input double InpOptTriggerR=1.0;
input double InpOptTrailATR=1.0;
input double InpOptADXMin=0.0;
input bool InpOptDI=false;
input int InpOptMaxTrades=0; // 0=original/unlimited (one simultaneous position)
input int InpOptSkipDays=0; // 1=Mon; 2=Fri; 3=both
#include "LTA Core.mqh"

int evFile=INVALID_HANDLE,eqFile=INVALID_HANDLE;
ulong flowId=0;
datetime flowEntry=0,lastFlowBar=0,lastTrace=0;
double frozenPOC=0,peakEq=10000,maxDD=0,maxDDCash=0;
double plannedRiskMoney=0;
bool partialDone=false,beDone=false;
int entries=0,partials=0,beMoves=0,minPartialSkips=0,orderFails=0,modifyFails=0,closeFails=0;
ProfileLevels plannedPD;
int optADXHandle=INVALID_HANDLE,optTradesToday=0;
datetime optDay=0;
double optInitialDistance=0;
double plannedVWAP=0,plannedDevPOC=0,plannedBody=0,plannedLocation=0;
datetime plannedBar=0;

string Prefix(){return "CalyxLTAOptimize20261005\\"+InpAuditTag;}
void Event(string kind,ulong id=0,int dir=0,double entry=0,double sl=0,double tp=0,double requested=0,double risk=0,string note="")
{
 if(evFile<0)return;
 FileWrite(evFile,(long)TimeCurrent(),kind,id,dir,entry,sl,tp,requested,risk,(long)plannedPD.from_time,(long)plannedPD.to_time,
  plannedPD.val,plannedPD.poc,plannedPD.vah,plannedVWAP,plannedDevPOC,(long)plannedBar,plannedBody,plannedLocation,note);
}
void Trace()
{
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);peakEq=MathMax(peakEq,eq);
 maxDDCash=MathMax(maxDDCash,peakEq-eq);if(peakEq>0)maxDD=MathMax(maxDD,100*(peakEq-eq)/peakEq);
 if(eqFile>=0 && TimeCurrent()-lastTrace>=300)
 {lastTrace=TimeCurrent();FileWrite(eqFile,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),eq,maxDD,maxDDCash);}
}
bool FlowProfile(ProfileLevels &pd,double &vwap,double &poc)
{
 datetime from=iTime(_Symbol,PERIOD_D1,1),to=iTime(_Symbol,PERIOD_D1,0),nowbar=iTime(_Symbol,PERIOD_M5,0);
 if(from<=0 || to<=from || nowbar<=to)return false;
 MqlRates past[],today[];
 int n=CopyRates(_Symbol,PERIOD_M5,from,(datetime)(to-1),past);
 if(n<8)return false;
 for(int i=0;i<n;i++)if(past[i].time<from || past[i].time>=to)return false;
 if(!CalculateProfileFromRates("FLOW_PD",past,n,from,to,pd))return false;
 n=CopyRates(_Symbol,PERIOD_M5,to,(datetime)(nowbar-1),today);
 if(n<8)return false;
 double amount=0,vol=0;
 for(int i=0;i<n;i++)
 {
  if(today[i].time<to || today[i].time+300>nowbar)return false;
  double v=BarVolume(today[i]);vol+=v;amount+=v*(today[i].high+today[i].low+today[i].close)/3;
 }
 ProfileLevels dev;if(vol<=0 || !CalculateProfileFromRates("FLOW_DEV",today,n,to,nowbar,dev))return false;
 vwap=amount/vol;poc=dev.poc;return true;
}
bool FlowQualifies(int dir,ProfileLevels &pd,double vwap,double poc,MqlRates &a,double entry)
{
 double range=a.high-a.low;if(range<=0)return false;
 double body=MathAbs(a.close-a.open)/range,location=(a.close-a.low)/range;
 if(a.close<pd.val || a.close>pd.vah || entry<pd.val || entry>pd.vah || body<0.60)return false;
 if(dir>0)return a.close>a.open && location>=0.75 && a.close>vwap && a.close>poc;
 return a.close<a.open && location<=0.25 && a.close<vwap && a.close<poc;
}
bool BuildSignal(TradeSignal &s)
{
 if(InpFlowMode==0)
 {
  datetime day=DayStart(TimeCurrent());if(day!=optDay){optDay=day;optTradesToday=0;}
  if(InpOptMaxTrades>0 && optTradesToday>=InpOptMaxTrades)return false;
  MqlDateTime clock;TimeToStruct(TimeCurrent(),clock);
  if((InpOptSkipDays==1 || InpOptSkipDays==3) && clock.day_of_week==1)return false;
  if((InpOptSkipDays==2 || InpOptSkipDays==3) && clock.day_of_week==5)return false;
  if(!BuildLegacySignal(s))return false;
  if(InpOptADXMin>0 || InpOptDI)
  {
   double strength[],plus[],minus[];
   if(BarsCalculated(optADXHandle)<30 || CopyBuffer(optADXHandle,0,1,1,strength)!=1 ||
      CopyBuffer(optADXHandle,1,1,1,plus)!=1 || CopyBuffer(optADXHandle,2,1,1,minus)!=1)return false;
   if(strength[0]<InpOptADXMin)return false;
   if(InpOptDI && (s.dir>0?plus[0]<=minus[0]:minus[0]<=plus[0]))return false;
  }
  double distance=MathAbs(s.entry-s.sl);
  if(InpOptStopMode==1)distance=GetATRValue(InpExecutionTF,14,1)*InpOptStopATR;
  if(InpOptStopMode==2)distance=s.entry*InpOptStopPricePct/100.0;
  distance*=InpOptStopFactor;
  // Recalculation is deliberately bypassed for exact off-switch parity.
  if(InpOptStopMode!=0 || InpOptStopFactor!=1.0)
  {
   s.sl=NormalizePrice(s.entry-s.dir*distance);
   s.tp=NormalizePrice(s.entry+s.dir*distance*InpRewardRisk);
  }
  if(!StopDistanceValid(s.dir,s.entry,s.sl) || s.dir*(s.tp-s.entry)<MinimumStopDistance())return false;
  return true;
 }
 ResetSignal(s);ProfileLevels pd;double vwap=0,poc=0;
 if(!FlowProfile(pd,vwap,poc))return false;
 MqlRates bars[];if(CopyRates(_Symbol,PERIOD_M5,1,3,bars)!=3)return false;
 ArraySetAsSeries(bars,true);MqlRates a=bars[0];
 TradeSignal legacy;ResetSignal(legacy);
 if(InpFlowMode==2 && !BuildLegacySignal(legacy))return false;
 int bias=GetMacroBias(),trend=GetTrendDirection(InpStructureTF);
 for(int d=0;d<2;d++)
 {
  int dir=d==0?1:-1;
  if(InpFlowMode==2 && legacy.dir!=dir)continue;
  if((dir>0 && !InpAllowLongs) || (dir<0 && !InpAllowShorts) || !DirectionAllowedByBias(dir,bias))continue;
  bool contra=(trend!=0 && trend!=dir);
  if((InpArchetype==LTA_ARCHETYPE_MOMENTUM && contra) || (InpArchetype==LTA_ARCHETYPE_CONTRARIAN && !contra))continue;
  double entry=SymbolInfoDouble(_Symbol,dir>0?SYMBOL_ASK:SYMBOL_BID);
  if(entry<=0 || !FlowQualifies(dir,pd,vwap,poc,a,entry))continue;
  double sl=dir>0?LowestLow(bars,3,0,3)-GetSLBuffer():HighestHigh(bars,3,0,3)+GetSLBuffer();
  if(InpFlowMode==2)sl=legacy.sl;
  double tp=dir>0?pd.vah:pd.val;
  sl=NormalizePrice(sl);tp=NormalizePrice(tp);
  if(!StopDistanceValid(dir,entry,sl) || dir*(tp-entry)<MinimumStopDistance())continue;
  s.valid=true;s.dir=dir;s.model=InpFlowMode==2?"AND-"+legacy.model:"VWAP-DevPOC";
  s.level_name="PD-VA";s.contrarian=contra;s.entry=entry;s.sl=sl;s.tp=tp;
  s.risk_percent=contra?InpContrarianRiskPercent:InpMomentumRiskPercent;
  plannedPD=pd;plannedVWAP=vwap;plannedDevPOC=poc;plannedBar=a.time;
  plannedBody=MathAbs(a.close-a.open)/(a.high-a.low);plannedLocation=(a.close-a.low)/(a.high-a.low);
  return true;
 }
 return false;
}
void FlowBeforeOrder(const TradeSignal &s)
{
 plannedRiskMoney=AccountInfoDouble(ACCOUNT_EQUITY)*MathMin(s.risk_percent,InpAbsoluteRiskCapPercent)/100;
}
void FlowAfterOrder(const TradeSignal &s,bool ok)
{
 if(!ok || m_trade.ResultRetcode()!=TRADE_RETCODE_DONE)
 {orderFails++;Event("order_failed",0,s.dir,s.entry,s.sl,s.tp,0,0,m_trade.ResultRetcodeDescription());return;}
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetInteger(POSITION_MAGIC)==InpMagicNumber && PositionGetString(POSITION_SYMBOL)==_Symbol){ticket=t;break;}
 }
 if(!ticket || !PositionSelectByTicket(ticket)){Print("FLOW_AUDIT_MISSING_POSITION");return;}
 entries++;flowId=(ulong)PositionGetInteger(POSITION_IDENTIFIER);flowEntry=(datetime)PositionGetInteger(POSITION_TIME);
 optTradesToday++;
 frozenPOC=plannedPD.poc;partialDone=false;beDone=false;lastFlowBar=0;
 double px=PositionGetDouble(POSITION_PRICE_OPEN),vol=PositionGetDouble(POSITION_VOLUME),risk=0;
 optInitialDistance=MathAbs(px-s.sl);
 bool calc=OrderCalcProfit(s.dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,vol,px,s.sl,risk);
 if(!calc){Print("FLOW_AUDIT_RISK_FAILED");return;}
 Event("entry",flowId,s.dir,px,s.sl,s.tp,plannedRiskMoney,MathAbs(risk),s.model+"|volume="+DoubleToString(vol,8));
}
void ManageOpt()
{
 if(InpOptManage==0 || optInitialDistance<=0)return;
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagicNumber &&
     (ulong)PositionGetInteger(POSITION_IDENTIFIER)==flowId){ticket=t;break;}
 }
 if(!ticket || !PositionSelectByTicket(ticket))return;
 int dir=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double px=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 double quote=SymbolInfoDouble(_Symbol,dir>0?SYMBOL_BID:SYMBOL_ASK);
 if(dir*(quote-px)<InpOptTriggerR*optInitialDistance)return;
 if(InpOptManage==3 && !partialDone)
 {
  double v=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double half=NormalizeDouble(MathFloor((v*0.5+1e-10)/step)*step,8);
  if(half>=minimum-1e-9 && v-half>=minimum-1e-9)
  {
   bool ok=m_trade.PositionClosePartial(ticket,half);
   if(ok && m_trade.ResultRetcode()==TRADE_RETCODE_DONE)
   {partialDone=true;partials++;Event("partial",flowId,dir,px,sl,tp,half,0,"research-half-at-R");}
   else{closeFails++;Event("partial_failed",flowId,dir,px,sl,tp,half,0,m_trade.ResultRetcodeDescription());return;}
  }
  else{partialDone=true;minPartialSkips++;Event("partial_minlot_skip",flowId,dir,px,sl,tp,v,0,"research-minimum-lot");}
 }
 double desired=px;
 if(InpOptManage==2)
 {
  double atr=GetATRValue(InpExecutionTF,14,1);if(atr<=0)return;
  desired=quote-dir*atr*InpOptTrailATR;
 }
 desired=NormalizePrice(desired);
 double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
 double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point+2*point;
 if(dir*(desired-sl)<=point || dir*(quote-desired)<=gap)return;
 bool ok=m_trade.PositionModify(ticket,desired,tp);
 if(ok && (m_trade.ResultRetcode()==TRADE_RETCODE_DONE || m_trade.ResultRetcode()==TRADE_RETCODE_NO_CHANGES))
 {
  if(InpOptManage!=2 && !beDone){beDone=true;beMoves++;Event("breakeven",flowId,dir,px,desired,tp,0,0,"research-BE");}
 }
 else{modifyFails++;Event("breakeven_failed",flowId,dir,px,desired,tp,0,0,m_trade.ResultRetcodeDescription());}
}
void ManageFlow()
{
 if(InpFlowMode==0)return;
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0 || bar==lastFlowBar)return;lastFlowBar=bar;
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetInteger(POSITION_MAGIC)==InpMagicNumber && PositionGetString(POSITION_SYMBOL)==_Symbol &&
   (ulong)PositionGetInteger(POSITION_IDENTIFIER)==flowId){ticket=t;break;}
 }
 if(!ticket || !PositionSelectByTicket(ticket))return;
 datetime closed=iTime(_Symbol,PERIOD_M5,1);double c=iClose(_Symbol,PERIOD_M5,1);
 if(closed<flowEntry || frozenPOC<=0)return;
 int dir=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 double quote=SymbolInfoDouble(_Symbol,dir>0?SYMBOL_BID:SYMBOL_ASK);
 if(dir*(c-frozenPOC)<=0 || dir*(quote-entry)<MinimumStopDistance())return;
 if(!partialDone)
 {
  double volume=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minvol=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double half=NormalizeDouble(MathFloor((volume*0.5+1e-10)/step)*step,8);
  if(half>=minvol-1e-9 && volume-half>=minvol-1e-9)
  {
   bool ok=m_trade.PositionClosePartial(ticket,half);
   if(ok && m_trade.ResultRetcode()==TRADE_RETCODE_DONE)
   {partialDone=true;partials++;Event("partial",flowId,dir,entry,sl,tp,half,frozenPOC,"close="+DoubleToString(c,_Digits)+"|bar="+(string)(long)closed);}
   else{closeFails++;Event("partial_failed",flowId,dir,entry,sl,tp,half,frozenPOC,m_trade.ResultRetcodeDescription());return;}
  }
  else{partialDone=true;minPartialSkips++;Event("partial_minlot_skip",flowId,dir,entry,sl,tp,volume,frozenPOC);}
 }
 if(!beDone && PositionSelectByTicket(ticket))
 {
  sl=PositionGetDouble(POSITION_SL);
  if(dir*(sl-entry)>=0){beDone=true;return;}
  bool ok=m_trade.PositionModify(ticket,NormalizePrice(entry),tp);
  if(ok && (m_trade.ResultRetcode()==TRADE_RETCODE_DONE || m_trade.ResultRetcode()==TRADE_RETCODE_NO_CHANGES))
  {beDone=true;beMoves++;Event("breakeven",flowId,dir,entry,entry,tp,0,frozenPOC,"close="+DoubleToString(c,_Digits)+"|bar="+(string)(long)closed);}
  else{modifyFails++;Event("breakeven_failed",flowId,dir,entry,entry,tp,0,frozenPOC,m_trade.ResultRetcodeDescription());}
 }
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpFlowMode!=0 || !InpOnePositionPerSymbol || InpAdaptivePortfolioControls)return INIT_PARAMETERS_INCORRECT;
 if(InpOptStopMode<0 || InpOptStopMode>2 || InpOptStopFactor<=0 || InpOptManage<0 || InpOptManage>3)return INIT_PARAMETERS_INCORRECT;
 if(InpOptManage>0 && (InpMoveAllBEAt1R || InpUseDynamicTrailingSL))return INIT_PARAMETERS_INCORRECT;
 if(InpFlowMode>0 && InpExecutionTF!=PERIOD_M5)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 evFile=FileOpen(Prefix()+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 eqFile=FileOpen(Prefix()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(evFile<0 || eqFile<0)return INIT_FAILED;
 FileWrite(evFile,"epoch","event","position_id","dir","entry","sl","tp","requested_risk","actual_risk","pd_from","pd_to","val","poc","vah","vwap","dev_poc","signal_epoch","body_fraction","close_location","note");
 FileWrite(eqFile,"epoch","balance","equity","max_dd_pct","max_dd_cash");
 peakEq=AccountInfoDouble(ACCOUNT_EQUITY);ResetProfile(plannedPD,"PD");
 if(InpOptADXMin>0 || InpOptDI){optADXHandle=iADX(_Symbol,InpExecutionTF,14);if(optADXHandle==INVALID_HANDLE)return INIT_FAILED;}
 return LTA_BaseInit();
}
void OnTick(){Trace();ManageOpt();LTA_BaseTick();Trace();}
double OnTester()
{
 Trace();int f=FileOpen(Prefix()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"deal","epoch","position_id","entry","type","reason","volume","price","gross","commission","swap","fee","comment");
 HistorySelect(0,TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong t=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(t,DEAL_TYPE);
  if(type>1 || HistoryDealGetInteger(t,DEAL_MAGIC)!=InpMagicNumber)continue;
  FileWrite(f,t,HistoryDealGetInteger(t,DEAL_TIME),HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_ENTRY),type,
   HistoryDealGetInteger(t,DEAL_REASON),HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),
   HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
 }
 FileClose(f);FileFlush(evFile);FileFlush(eqFile);
 PrintFormat("FLOW_SUMMARY entries=%d partials=%d be=%d minpartial=%d orders_failed=%d close_failed=%d modify_failed=%d maxdd=%.8f cashdd=%.8f",entries,partials,beMoves,minPartialSkips,orderFails,closeFails,modifyFails,maxDD,maxDDCash);
 return LTA_BaseScore();
}
void OnDeinit(const int reason){if(evFile>=0)FileClose(evFile);if(eqFile>=0)FileClose(eqFile);if(optADXHandle!=INVALID_HANDLE)IndicatorRelease(optADXHandle);}

// Research only: existing LTA entry logic with isolated AOI exit hooks.
input int InpExitCase=0; // 0=3R, 1=PD TP, 2=PW TP, 3=both TP, 4=frozen trail, 5=rolling trail
input int InpAuditRun=0;
#include "LTA Original Core.mqh"

int aoiFile=INVALID_HANDLE,eqFile=INVALID_HANDLE;
double ladder[],plannedLadder[];
string ladderNames[],plannedNames[];
double entryPrice=0,entryBuffer=0;
datetime entryTime=0,lastTrailBar=0,loadedDay=0,loadedWeek=0;
datetime firstTick=0,lastTick=0,lastEq=0;
ulong positionId=0;
int targets=0,fallbacks=0,trails=0,modifyFailures=0,orderFailures=0,entries=0;
double initialEquity=0,peakEquity=0,minEquity=DBL_MAX,maxDD=0,maxDDCash=0;
string auditPrefix;

string Stamp(datetime t){return t>0?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
string LadderText(double &a[],string &names[])
{
 string result="";
 for(int i=0;i<ArraySize(a);i++)result+=(i?";":"")+names[i]+"="+DoubleToString(a[i],_Digits);
 return result;
}
void Audit(string event,int dir=0,double price=0,double sl=0,double tp=0,string note="",double broken=0,double prior=0,double close1=0,double close2=0,double oldSL=0,datetime bar=0)
{
 if(aoiFile<0)return;
 FileWrite(aoiFile,Stamp(TimeCurrent()),event,positionId,dir,price,sl,tp,note,entryBuffer,broken,prior,close1,close2,oldSL,Stamp(bar),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),LadderText(ladder,ladderNames));
}
double TickRound(double x,int dir)
{
 double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(ts<=0)ts=_Point;
 return NormalizeDouble((dir>0?MathFloor(x/ts+1e-9):MathCeil(x/ts-1e-9))*ts,_Digits);
}
void AddLevel(double &a[],string &names[],double x,string name)
{
 if(x<=0)return;
 for(int i=0;i<ArraySize(a);i++)if(MathAbs(a[i]-x)<_Point/2){names[i]+="+"+name;return;}
 int n=ArraySize(a);ArrayResize(a,n+1);ArrayResize(names,n+1);a[n]=x;names[n]=name;
 for(int i=n;i>0 && a[i]<a[i-1];i--){double q=a[i-1];a[i-1]=a[i];a[i]=q;string s=names[i-1];names[i-1]=names[i];names[i]=s;}
}
bool ExitProfile(ENUM_TIMEFRAMES period,string name,ProfileLevels &p)
{
 ResetProfile(p,name);
 datetime from=iTime(_Symbol,period,1),to=iTime(_Symbol,period,0);
 if(from<=0 || to<=from || to>TimeCurrent())return false;
 MqlRates rates[];int n=CopyRates(_Symbol,InpProfileTF,from,(datetime)(to-1),rates);
 if(n<8)return false;
 for(int i=0;i<n;i++)if(rates[i].time<from || rates[i].time>=to)return false;
 ArraySetAsSeries(rates,true);
 return CalculateProfileFromRates(name,rates,n,from,to,p);
}
void LoadLadder(int scope,double &a[],string &names[])
{
 ArrayResize(a,0);ArrayResize(names,0);
 ProfileLevels p;
 if(scope!=2 && ExitProfile(PERIOD_D1,"PD",p))
 {AddLevel(a,names,p.poc,"PD.POC");AddLevel(a,names,p.vah,"PD.VAH");AddLevel(a,names,p.val,"PD.VAL");}
 if(scope!=1 && ExitProfile(PERIOD_W1,"PW",p))
 {AddLevel(a,names,p.poc,"PW.POC");AddLevel(a,names,p.vah,"PW.VAH");AddLevel(a,names,p.val,"PW.VAL");}
}
bool AOI_AdjustTarget(int dir,double entry,double sl,double &tp)
{
 if(InpExitCase==0)return true;
 int scope=InpExitCase<=3?InpExitCase:3;
 LoadLadder(scope,plannedLadder,plannedNames);
 if(InpExitCase>=4){tp=0;return true;}
 double best=DBL_MAX,chosen=0;
 for(int i=0;i<ArraySize(plannedLadder);i++)
 {
  double target=TickRound(plannedLadder[i],dir),distance=dir*(target-entry);
  if(distance>=MinimumStopDistance() && distance<best){best=distance;chosen=target;}
 }
 if(chosen>0)tp=chosen; // Explicit original 3R fallback if no favorable AOI.
 return true;
}
void AOI_AfterOrder(const TradeSignal &s,bool ok)
{
 if(!ok || m_trade.ResultRetcode()!=TRADE_RETCODE_DONE)
 {orderFailures++;Audit("order_failed",s.dir,s.entry,s.sl,s.tp,m_trade.ResultRetcodeDescription());return;}
 ulong found=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetInteger(POSITION_MAGIC)==InpMagicNumber && PositionGetString(POSITION_SYMBOL)==_Symbol){found=t;break;}
 }
 if(!found || !PositionSelectByTicket(found)){Audit("missing_position");return;}
 entries++;positionId=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
 entryPrice=PositionGetDouble(POSITION_PRICE_OPEN);entryTime=(datetime)PositionGetInteger(POSITION_TIME);
 entryBuffer=MathMax(0.05*GetATRValue(InpExecutionTF,14,1),2*_Point);
 if(InpExitCase>0)
 {
  ArrayResize(ladder,ArraySize(plannedLadder));ArrayResize(ladderNames,ArraySize(plannedNames));
  ArrayCopy(ladder,plannedLadder);ArrayCopy(ladderNames,plannedNames);
 }
 else {ArrayResize(ladder,0);ArrayResize(ladderNames,0);}
 loadedDay=iTime(_Symbol,PERIOD_D1,0);loadedWeek=iTime(_Symbol,PERIOD_W1,0);
 string kind="fixed_3R";
 if(InpExitCase>0 && InpExitCase<4)
 {
  bool matched=false;
  for(int i=0;i<ArraySize(ladder);i++)if(MathAbs(TickRound(ladder[i],s.dir)-s.tp)<_Point/2)matched=true;
  if(matched){targets++;kind="aoi_target";}else{fallbacks++;kind="fallback_3R";}
 }
 if(InpExitCase>=4)kind="no_tp";
 double risk=0;
 if(!OrderCalcProfit(s.dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,PositionGetDouble(POSITION_VOLUME),entryPrice,s.sl,risk))
 {Audit("risk_calc_failed");return;}
 Audit("entry",s.dir,entryPrice,s.sl,s.tp,kind+"|risk="+DoubleToString(MathAbs(risk),4)+"|volume="+DoubleToString(PositionGetDouble(POSITION_VOLUME),4)+"|PD="+Stamp(loadedDay)+"|PW="+Stamp(loadedWeek));
}
void TrailAOI()
{
 if(InpExitCase<4)return;
 datetime currentBar=iTime(_Symbol,InpExecutionTF,0);
 if(!currentBar || currentBar==lastTrailBar)return;
 lastTrailBar=currentBar;
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetInteger(POSITION_MAGIC)==InpMagicNumber && PositionGetString(POSITION_SYMBOL)==_Symbol){ticket=t;break;}
 }
 if(!ticket || !PositionSelectByTicket(ticket))return;
 int dir=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 datetime closedBar=iTime(_Symbol,InpExecutionTF,1);
 double c1=iClose(_Symbol,InpExecutionTF,1),c2=iClose(_Symbol,InpExecutionTF,2);
 double old=PositionGetDouble(POSITION_SL),candidate=old,broken=0,previous=0;
 if(closedBar>=entryTime && c1>0 && c2>0)
 {
  for(int i=0;i<ArraySize(ladder);i++)
  {
   int prev=i-dir;
   if(prev<0 || prev>=ArraySize(ladder) || dir*(ladder[i]-entryPrice)<=0)continue;
   double threshold=ladder[i]+dir*entryBuffer;
   if(dir*(c1-threshold)<=0 || dir*(c2-threshold)>0)continue;
   double proposed=TickRound(ladder[prev]-dir*entryBuffer,dir);
   if(dir*(proposed-candidate)>_Point/2){candidate=proposed;broken=ladder[i];previous=ladder[prev];}
  }
  if(dir*(candidate-old)>_Point/2)
  {
   double quote=SymbolInfoDouble(_Symbol,dir>0?SYMBOL_BID:SYMBOL_ASK);
   if(dir*(quote-candidate)>=MinimumStopDistance())
   {
    bool ok=m_trade.PositionModify(ticket,candidate,0);
    bool accepted=ok && (m_trade.ResultRetcode()==TRADE_RETCODE_DONE || m_trade.ResultRetcode()==TRADE_RETCODE_NO_CHANGES);
    if(accepted)trails++;else modifyFailures++;
    Audit(accepted?"trail":"trail_failed",dir,entryPrice,candidate,0,m_trade.ResultRetcodeDescription(),broken,previous,c1,c2,old,closedBar);
   }
   else Audit("trail_distance_rejected",dir,entryPrice,candidate,0,"old SL retained",broken,previous,c1,c2,old,closedBar);
  }
 }
 // New profiles are available to future candles only, never retroactively.
 datetime d=iTime(_Symbol,PERIOD_D1,0),w=iTime(_Symbol,PERIOD_W1,0);
 if(InpExitCase==5 && (d!=loadedDay || w!=loadedWeek))
 {
  LoadLadder(3,ladder,ladderNames);loadedDay=d;loadedWeek=w;
  Audit("ladder_refresh",dir,entryPrice,PositionGetDouble(POSITION_SL),0,"PD="+Stamp(d)+"|PW="+Stamp(w));
 }
}
void Track()
{
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);peakEquity=MathMax(peakEquity,eq);minEquity=MathMin(minEquity,eq);
 maxDDCash=MathMax(maxDDCash,peakEquity-eq);if(peakEquity>0)maxDD=MathMax(maxDD,100*(peakEquity-eq)/peakEquity);
 if(eqFile>=0 && TimeCurrent()-lastEq>=900)
 {lastEq=TimeCurrent();FileWrite(eqFile,Stamp(TimeCurrent()),AccountInfoDouble(ACCOUNT_BALANCE),eq,maxDD,maxDDCash);}
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpExitCase<0 || InpExitCase>5 || !InpOnePositionPerSymbol || InpAdaptivePortfolioControls || InpUseDynamicTrailingSL)return INIT_PARAMETERS_INCORRECT;
 initialEquity=AccountInfoDouble(ACCOUNT_BALANCE);peakEquity=initialEquity;minEquity=initialEquity;
 auditPrefix="LTA-AOI-"+(string)InpAuditRun+"-"+(string)InpExitCase;
 aoiFile=FileOpen(auditPrefix+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 eqFile=FileOpen(auditPrefix+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(aoiFile<0 || eqFile<0)return INIT_FAILED;
 FileWrite(aoiFile,"time","event","position_id","dir","entry","sl","tp","note","buffer","broken","previous","close1","close2","old_sl","closed_bar","balance","equity","ladder");
 FileWrite(eqFile,"time","balance","equity","max_dd_pct","max_dd_cash");
 Print("AOI CONTRACT symbol=",_Symbol," contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," leverage=",AccountInfoInteger(ACCOUNT_LEVERAGE)," case=",InpExitCase);
 return LTA_BaseInit();
}
void OnTick()
{
 if(!firstTick)firstTick=TimeCurrent();lastTick=TimeCurrent();Track();TrailAOI();LTA_BaseTick();Track();
}
void SummaryValue(int f,string key,double v){FileWrite(f,key,DoubleToString(v,8));}
double OnTester()
{
 Track();int f=FileOpen(auditPrefix+"-summary.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 FileWrite(f,"key","value");FileWrite(f,"first_tick",Stamp(firstTick));FileWrite(f,"last_tick",Stamp(lastTick));
 SummaryValue(f,"initial_balance",initialEquity);SummaryValue(f,"final_balance",AccountInfoDouble(ACCOUNT_BALANCE));
 SummaryValue(f,"native_net_profit",TesterStatistics(STAT_PROFIT));SummaryValue(f,"native_trades",TesterStatistics(STAT_TRADES));
 SummaryValue(f,"native_pf",TesterStatistics(STAT_PROFIT_FACTOR));SummaryValue(f,"native_dd_pct",TesterStatistics(STAT_EQUITY_DDREL_PERCENT));
 SummaryValue(f,"max_dd_pct",maxDD);SummaryValue(f,"max_dd_cash",maxDDCash);SummaryValue(f,"minimum_equity",minEquity);
 SummaryValue(f,"entries",entries);SummaryValue(f,"aoi_targets",targets);SummaryValue(f,"fallbacks",fallbacks);SummaryValue(f,"trails",trails);
 SummaryValue(f,"modify_failures",modifyFailures);SummaryValue(f,"order_failures",orderFailures);FileClose(f);
 int deals=FileOpen(auditPrefix+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 FileWrite(deals,"deal","time","time_msc","symbol","position_id","type","entry","reason","volume","price","profit","commission","swap","fee","comment");
 HistorySelect(0,TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong t=HistoryDealGetTicket(i);
  FileWrite(deals,t,Stamp((datetime)HistoryDealGetInteger(t,DEAL_TIME)),HistoryDealGetInteger(t,DEAL_TIME_MSC),HistoryDealGetString(t,DEAL_SYMBOL),HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_TYPE),HistoryDealGetInteger(t,DEAL_ENTRY),HistoryDealGetInteger(t,DEAL_REASON),HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
 }
 FileClose(deals);FileFlush(aoiFile);FileFlush(eqFile);return LTA_BaseScore();
}
void OnDeinit(const int reason)
{
 if(aoiFile>=0)FileClose(aoiFile);if(eqFile>=0)FileClose(eqFile);
}

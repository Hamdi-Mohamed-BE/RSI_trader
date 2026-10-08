#property strict
#property version "3.00"
#include <Trade/Trade.mqh>
#include "CalyxAdaptivePortfolio.mqh"
#include "RiskSupport.mqh"




enum Profile { AUTO_PROFILE=0, US30_PROFILE=1, US100_PROFILE=2, SP500_PROFILE=3, CUSTOM_PROFILE=4 };
input Profile InpProfile=AUTO_PROFILE;
input string InpBuyHours="";
input string InpSellHours="";
input double InpLots=1.0;
input int InpSizingMode=1; // 0=frozen fixed lots, 1=balance percent, 2=fixed account cash
input double InpRiskPercent=0.5;
input double InpFixedRiskMoney=50.0;
input double InpHistoricalLossPoints=0;
input bool InpAdaptivePortfolioControls=false;
input int InpEntryMinute=0;
input int InpHoldMinutes=60;
input long InpMagic=103310;
input bool InpAllowRealAccount=false;
input bool InpAutoServerUTC=true;
input int InpServerUTCOffsetMinutes=0;
input string InpAuditTag="hour-profile";
CTrade trade;
int directions[24], lastDay[24];
string prefix;
bool hourlyCycleBusy=false;
datetime closeRetry=0, curveMinute=0;
double equityPeak=0,maxEquityDD=0,minimumEquity=0,minuteMin=0,minuteMax=0;
int curveFile=INVALID_HANDLE,fillFile=INVALID_HANDLE;
int attempted=0,accepted=0,blocked=0,closeFailures=0,checksRejected=0;

int Sunday(int y,int m,int n){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=1;TimeToStruct(StructToTime(x),x);return 1+(7-x.day_of_week)%7+7*(n-1);}
datetime NY(datetime utc){MqlDateTime x,a,b;TimeToStruct(utc,x);ZeroMemory(a);ZeroMemory(b);a.year=x.year;a.mon=3;a.day=Sunday(x.year,3,2);a.hour=7;b.year=x.year;b.mon=11;b.day=Sunday(x.year,11,1);b.hour=6;return utc-((utc>=StructToTime(a)&&utc<StructToTime(b))?4:5)*3600;}
int Offset(){if(MQLInfoInteger(MQL_TESTER)||!InpAutoServerUTC)return InpServerUTCOffsetMinutes*60;return (int)MathRound((double)(TimeTradeServer()-TimeGMT())/900.)*900;}
datetime UTC(){return (MQLInfoInteger(MQL_TESTER)?TimeCurrent():TimeTradeServer())-Offset();}
uint Hash(string s){uint v=2166136261;for(int i=0;i<StringLen(s);i++){v^=(uint)StringGetCharacter(s,i);v*=16777619;}return v;}
string Key(int h){return prefix+IntegerToString(h);}
bool Parse(string text,int side){if(text=="")return true;string a[];int n=StringSplit(text,',',a);for(int i=0;i<n;i++){StringTrimLeft(a[i]);StringTrimRight(a[i]);int h=(int)StringToInteger(a[i]);if(h<0||h>23||IntegerToString(h)!=a[i]||(directions[h]!=0&&directions[h]!=side))return false;directions[h]=side;}return true;}
bool Own(){return PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic;}
int Owned(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0&&Own())n++;return n;}
bool Session(datetime server){MqlDateTime d;TimeToStruct(server,d);int sec=d.hour*3600+d.min*60+d.sec;datetime a,b;bool known=false;for(uint i=0;i<20;i++){if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;known=true;int from=(int)a%86400,to=(int)b%86400;if(from==to||(from<to&&sec>=from&&sec<to)||(from>to&&(sec>=from||sec<to)))return true;}return !known;}
void Mark(){if(!MQLInfoInteger(MQL_TESTER))return;double e=AccountInfoDouble(ACCOUNT_EQUITY);equityPeak=MathMax(equityPeak,e);minimumEquity=MathMin(minimumEquity,e);if(equityPeak>0)maxEquityDD=MathMax(maxEquityDD,100*(equityPeak-e)/equityPeak);datetime m=UTC()/60*60;if(curveMinute!=m){if(curveMinute>0)FileWrite(curveFile,curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),e,minuteMin,minuteMax);curveMinute=m;minuteMin=e;minuteMax=e;}else{minuteMin=MathMin(minuteMin,e);minuteMax=MathMax(minuteMax,e);}}

double HistoricalSizedLots(const int side,const MqlTick &tick)
{
 if(InpSizingMode==0) return InpLots; // Exact frozen fixed-lot benchmark.
 double multiplier=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
 if(multiplier<=0) return 0;
 double budget=(InpSizingMode==2 ? InpFixedRiskMoney : AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0)*multiplier;
 double sample=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
 double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double price=(side>0 ? tick.ask : tick.bid);
 if(!MathIsValidNumber(budget)||budget<=0||sample<=0||tickSize<=0) return 0;
 // The reference includes historical net costs expressed in index price units.
 // It is a synthetic adverse move for sizing, NOT a placed protective stop.
 double distance=MathCeil(InpHistoricalLossPoints/tickSize)*tickSize;
 double exitPrice=NormalizeDouble(price+(side>0 ? -distance : distance),_Digits);
 double projected=0;
 if(exitPrice<=0||!OrderCalcProfit(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,_Symbol,sample,price,exitPrice,projected)||!MathIsValidNumber(projected)||projected>=0) return 0;
 double lossPerLot=-projected/sample;
 double requested=budget/lossPerLot;
 if(!MathIsValidNumber(requested)||requested<=0) return 0;
 PrintFormat("HOURLY_HISTORICAL_SIZE budget=%.2f historical_points=%.8f requested_lots=%.8f; NO SL, future loss can exceed reference",budget,InpHistoricalLossPoints,requested);
 return requested;
}

void Cycle(){
 if(hourlyCycleBusy)return;hourlyCycleBusy=true;datetime now=UTC();Mark();
 // Recover the scheduled exit from the broker position, not volatile RAM.
 for(int i=PositionsTotal()-1;i>=0;i--){ulong ticket=PositionGetTicket(i);if(!ticket||!Own())continue;datetime entered=(datetime)PositionGetInteger(POSITION_TIME)-Offset();MqlDateTime d;TimeToStruct(NY(entered),d);int day=d.year*10000+d.mon*100+d.day;if(lastDay[d.hour]!=day){lastDay[d.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(Key(d.hour),day);GlobalVariablesFlush();}}datetime expiry=(entered/60*60)+InpHoldMinutes*60;if(now>=expiry&&now>=closeRetry){closeRetry=now+5;if(Session(now+Offset())){bool ok=trade.PositionClose(ticket);uint rc=trade.ResultRetcode();if(!ok||(rc!=TRADE_RETCODE_DONE&&rc!=TRADE_RETCODE_DONE_PARTIAL)){closeFailures++;closeRetry=now+30;Print("HOURLY_CLOSE_REJECT ",ticket," ",rc);}}}}
 MqlDateTime ny;TimeToStruct(NY(now),ny);int day=ny.year*10000+ny.mon*100+ny.day;
 if(ny.day_of_week==0||ny.day_of_week==6||ny.min!=InpEntryMinute||directions[ny.hour]==0||lastDay[ny.hour]==day){hourlyCycleBusy=false;return;}
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)||MathAbs((double)(tick.time-Offset()-now))>3||tick.bid<=0||tick.ask<=0){hourlyCycleBusy=false;return;}
 // Consume signal before any request: manual close/restart cannot re-enter it.
 lastDay[ny.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(Key(ny.hour),day);GlobalVariablesFlush();}
 if(Owned()>0||!Session(now+Offset())){blocked++;hourlyCycleBusy=false;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 double requested=HistoricalSizedLots(directions[ny.hour],tick);
 if(!MathIsValidNumber(requested)||requested<=0||step<=0||lo<=0||hi<lo){blocked++;hourlyCycleBusy=false;return;}
 double lots=NormalizeDouble(lo+MathMax(0.0,MathFloor((requested-lo)/step+1e-10))*step,8);
 if(lots>hi){blocked++;hourlyCycleBusy=false;return;}
 if(lots>requested+1e-8)Print("HOURLY_MINIMUM_OVERRIDE requested=",requested," actual=",lots,"; historical scenario budget exceeded; NO loss cap");
 else if(MathAbs(lots-requested)>1e-8)Print("HOURLY_VOLUME_ROUNDED_DOWN requested=",requested," actual=",lots,"; NO future loss cap");
 MqlTradeRequest req;MqlTradeCheckResult check;ZeroMemory(req);ZeroMemory(check);req.action=TRADE_ACTION_DEAL;req.magic=InpMagic;req.symbol=_Symbol;req.volume=lots;req.type=directions[ny.hour]>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;req.price=directions[ny.hour]>0?tick.ask:tick.bid;req.deviation=30;
 long fill=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);req.type_filling=((fill&SYMBOL_FILLING_FOK)!=0)?ORDER_FILLING_FOK:(((fill&SYMBOL_FILLING_IOC)!=0)?ORDER_FILLING_IOC:ORDER_FILLING_RETURN);
 if(!OrderCheck(req,check)||(check.retcode!=0&&check.retcode!=TRADE_RETCODE_DONE)){checksRejected++;Print("HOURLY_CHECK_REJECT ",check.retcode," ",check.comment);hourlyCycleBusy=false;return;}
 attempted++;string comment="NYH|"+IntegerToString(ny.hour)+"|"+IntegerToString(day);bool ok=directions[ny.hour]>0?trade.Buy(lots,_Symbol,0,0,0,comment):trade.Sell(lots,_Symbol,0,0,0,comment);uint rc=trade.ResultRetcode();
 if(ok&&(rc==TRADE_RETCODE_DONE||rc==TRADE_RETCODE_DONE_PARTIAL))accepted++;else Print("HOURLY_ENTRY_REJECT ",ny.hour," ",rc,"; consumed, no blind retry");
 if(fillFile!=INVALID_HANDLE)FileWrite(fillFile,now,ny.hour,directions[ny.hour],tick.bid,tick.ask,trade.ResultPrice(),trade.ResultDeal(),rc,lots);
 hourlyCycleBusy=false;
}
int OnInit(){
 if(!FP_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;
 if(InpSizingMode<0||InpSizingMode>2||!MathIsValidNumber(InpRiskPercent)||InpRiskPercent<=0||InpRiskPercent>10||!MathIsValidNumber(InpFixedRiskMoney)||InpFixedRiskMoney<=0)return INIT_PARAMETERS_INCORRECT;
 if(InpSizingMode!=0&&(!MathIsValidNumber(InpHistoricalLossPoints)||InpHistoricalLossPoints<=0))return INIT_PARAMETERS_INCORRECT;
 if(InpLots<=0||InpMagic<=0||InpEntryMinute<0||InpEntryMinute>59||InpHoldMinutes<1||InpHoldMinutes>180)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Separate position ownership requires a hedging account.");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL&&!InpAllowRealAccount&&!MQLInfoInteger(MQL_TESTER)){Print("Research/demo default: real-account use disabled.");return INIT_FAILED;}
 ArrayInitialize(directions,0);ArrayInitialize(lastDay,0);int p=(int)InpProfile;
 if(p==0){string s=_Symbol+" "+SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION);StringToUpper(s);if(StringFind(s,"US30")>=0||StringFind(s,"WALL STREET")>=0||StringFind(s,"DJ30")>=0||StringFind(s,"DOW")>=0)p=1;else if(StringFind(s,"USTEC")>=0||StringFind(s,"US100")>=0||StringFind(s,"NASDAQ")>=0||StringFind(s,"US TECH")>=0)p=2;else if(StringFind(s,"US500")>=0||StringFind(s,"SP500")>=0||StringFind(s,"SPX500")>=0||StringFind(s,"S&P")>=0)p=3;else return INIT_PARAMETERS_INCORRECT;}
 string buy=InpBuyHours,sell=InpSellHours;if(buy==""&&sell==""){if(p==1){buy="2,6";sell="0,15,22";}else if(p==2){buy="2,13,20";sell="14,22";}else if(p==3){sell="22";}else return INIT_PARAMETERS_INCORRECT;}
 if(!Parse(buy,1)||!Parse(sell,-1))return INIT_PARAMETERS_INCORRECT;
 prefix="NYH."+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"."+IntegerToString(Hash(_Symbol+AccountInfoString(ACCOUNT_SERVER)+IntegerToString(InpMagic)))+".";
 if(!MQLInfoInteger(MQL_TESTER))for(int h=0;h<24;h++)if(GlobalVariableCheck(Key(h)))lastDay[h]=(int)GlobalVariableGet(Key(h));
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(30);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 equityPeak=minimumEquity=AccountInfoDouble(ACCOUNT_EQUITY);
 if(MQLInfoInteger(MQL_TESTER)){curveFile=FileOpen(InpAuditTag+"-curve.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');fillFile=FileOpen(InpAuditTag+"-fills.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(curveFile==INVALID_HANDLE||fillFile==INVALID_HANDLE)return INIT_FAILED;FileWrite(curveFile,"utc_minute","balance_at_next_sample","equity_at_next_sample","minimum_equity","maximum_equity");FileWrite(fillFile,"utc","ny_hour","side","bid","ask","fill_price","deal","retcode","lots");}
 EventSetTimer(5);Print("HOURLY_INIT profile=",p," BUY=",buy," SELL=",sell," sizingMode=",InpSizingMode," historicalLossPoints=",InpHistoricalLossPoints," riskPercent=",InpRiskPercent," NO SL/TP; historical scenario, NOT a loss cap; server UTC offset=",Offset());FP_Heartbeat(InpMagic,true);return INIT_SUCCEEDED;
}
void OnTick(){
 if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);Cycle();}
void OnTimer(){
 if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);Cycle();}
void OnDeinit(const int reason){EventKillTimer();if(curveFile!=INVALID_HANDLE){if(curveMinute>0)FileWrite(curveFile,curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),minuteMin,minuteMax);FileClose(curveFile);}if(fillFile!=INVALID_HANDLE)FileClose(fillFile);}
double OnTester(){
 HistorySelect(0,TimeCurrent());int f=FileOpen(InpAuditTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"ticket","position_id","time_msc","magic","entry","type","volume","price","profit","commission","swap","fee","comment");
 for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);if(HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic||HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol)continue;FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));}FileClose(f);
 Mark();f=FileOpen(InpAuditTag+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"attempted","accepted","blocked","checks_rejected","close_failures","max_equity_dd_pct","minimum_equity");FileWrite(f,attempted,accepted,blocked,checksRejected,closeFailures,maxEquityDD,minimumEquity);FileClose(f);Print("HOURLY_COMPLETE attempted=",attempted," accepted=",accepted," blocked=",blocked," checks=",checksRejected," closeFailures=",closeFailures);return 0;
}

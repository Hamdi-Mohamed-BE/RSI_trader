#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
#include "../_Shared/CalyxAdaptivePortfolio.mqh"
input int InpCase=0; // 0=all, 1..5=one module only


const string H30_Symbol="US30";
const ENUM_TIMEFRAMES H30_Period=(ENUM_TIMEFRAMES)1;




enum H30_Profile { H30_AUTO_PROFILE=0, H30_US30_PROFILE=1, H30_US100_PROFILE=2, H30_SP500_PROFILE=3, H30_CUSTOM_PROFILE=4 };
const H30_Profile H30_InpProfile=(H30_Profile)1;
const string H30_InpBuyHours="";
const string H30_InpSellHours="";
const double H30_InpLots=1.0;
const int H30_InpSizingMode=1; // 0=frozen fixed lots, 1=balance percent, 2=fixed account cash
const double H30_InpRiskPercent=1.0;
const double H30_InpFixedRiskMoney=50.0;
const double H30_InpHistoricalLossPoints=611.53000;
const bool H30_InpAdaptivePortfolioControls=false;
const int H30_InpEntryMinute=0;
const int H30_InpHoldMinutes=60;
const long H30_InpMagic=104103301;
const bool H30_InpAllowRealAccount=false;
const bool H30_InpAutoServerUTC=true;
const int H30_InpServerUTCOffsetMinutes=0;
const string H30_InpAuditTag="five20261007-H30";
CTrade H30_trade;
int H30_directions[24], H30_lastDay[24];
string H30_prefix;
bool H30_hourlyCycleBusy=false;
datetime H30_closeRetry=0, H30_curveMinute=0;
double H30_equityPeak=0,H30_maxEquityDD=0,H30_minimumEquity=0,H30_minuteMin=0,H30_minuteMax=0;
int H30_curveFile=INVALID_HANDLE,H30_fillFile=INVALID_HANDLE;
int H30_attempted=0,H30_accepted=0,H30_blocked=0,H30_closeFailures=0,H30_checksRejected=0;

int H30_Sunday(int y,int m,int n){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=1;TimeToStruct(StructToTime(x),x);return 1+(7-x.day_of_week)%7+7*(n-1);}
datetime H30_NY(datetime utc){MqlDateTime x,a,b;TimeToStruct(utc,x);ZeroMemory(a);ZeroMemory(b);a.year=x.year;a.mon=3;a.day=H30_Sunday(x.year,3,2);a.hour=7;b.year=x.year;b.mon=11;b.day=H30_Sunday(x.year,11,1);b.hour=6;return utc-((utc>=StructToTime(a)&&utc<StructToTime(b))?4:5)*3600;}
int H30_Offset(){if(MQLInfoInteger(MQL_TESTER)||!H30_InpAutoServerUTC)return H30_InpServerUTCOffsetMinutes*60;return (int)MathRound((double)(TimeTradeServer()-TimeGMT())/900.)*900;}
datetime H30_UTC(){return (MQLInfoInteger(MQL_TESTER)?TimeCurrent():TimeTradeServer())-H30_Offset();}
uint H30_Hash(string s){uint v=2166136261;for(int i=0;i<StringLen(s);i++){v^=(uint)StringGetCharacter(s,i);v*=16777619;}return v;}
string H30_Key(int h){return H30_prefix+IntegerToString(h);}
bool H30_Parse(string text,int side){if(text=="")return true;string a[];int n=StringSplit(text,',',a);for(int i=0;i<n;i++){StringTrimLeft(a[i]);StringTrimRight(a[i]);int h=(int)StringToInteger(a[i]);if(h<0||h>23||IntegerToString(h)!=a[i]||(H30_directions[h]!=0&&H30_directions[h]!=side))return false;H30_directions[h]=side;}return true;}
bool H30_Own(){return PositionGetString(POSITION_SYMBOL)==H30_Symbol&&PositionGetInteger(POSITION_MAGIC)==H30_InpMagic;}
int H30_Owned(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0&&H30_Own())n++;return n;}
bool H30_Session(datetime server){MqlDateTime d;TimeToStruct(server,d);int sec=d.hour*3600+d.min*60+d.sec;datetime a,b;bool known=false;for(uint i=0;i<20;i++){if(!SymbolInfoSessionTrade(H30_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;known=true;int from=(int)a%86400,to=(int)b%86400;if(from==to||(from<to&&sec>=from&&sec<to)||(from>to&&(sec>=from||sec<to)))return true;}return !known;}
void H30_Mark(){if(!MQLInfoInteger(MQL_TESTER))return;double e=AccountInfoDouble(ACCOUNT_EQUITY);H30_equityPeak=MathMax(H30_equityPeak,e);H30_minimumEquity=MathMin(H30_minimumEquity,e);if(H30_equityPeak>0)H30_maxEquityDD=MathMax(H30_maxEquityDD,100*(H30_equityPeak-e)/H30_equityPeak);datetime m=H30_UTC()/60*60;if(H30_curveMinute!=m){if(H30_curveMinute>0)FileWrite(H30_curveFile,H30_curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),e,H30_minuteMin,H30_minuteMax);H30_curveMinute=m;H30_minuteMin=e;H30_minuteMax=e;}else{H30_minuteMin=MathMin(H30_minuteMin,e);H30_minuteMax=MathMax(H30_minuteMax,e);}}

double H30_HistoricalSizedLots(const int side,const MqlTick &tick)
{
 if(H30_InpSizingMode==0) return H30_InpLots; // Exact frozen fixed-lot benchmark.
 double multiplier=CalyxAdaptiveRiskMultiplier(H30_InpAdaptivePortfolioControls,H30_InpMagic);
 if(multiplier<=0) return 0;
 double budget=(H30_InpSizingMode==2 ? H30_InpFixedRiskMoney : AccountInfoDouble(ACCOUNT_BALANCE)*H30_InpRiskPercent/100.0)*multiplier;
 double sample=MathMax(SymbolInfoDouble(H30_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(H30_Symbol,SYMBOL_VOLUME_STEP));
 double tickSize=SymbolInfoDouble(H30_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double price=(side>0 ? tick.ask : tick.bid);
 if(!MathIsValidNumber(budget)||budget<=0||sample<=0||tickSize<=0) return 0;
 // The reference includes historical net costs expressed in index price units.
 // It is a synthetic adverse move for sizing, NOT a placed protective stop.
 double distance=MathCeil(H30_InpHistoricalLossPoints/tickSize)*tickSize;
 double exitPrice=NormalizeDouble(price+(side>0 ? -distance : distance),((int)SymbolInfoInteger(H30_Symbol,SYMBOL_DIGITS)));
 double projected=0;
 if(exitPrice<=0||!OrderCalcProfit(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,H30_Symbol,sample,price,exitPrice,projected)||!MathIsValidNumber(projected)||projected>=0) return 0;
 double lossPerLot=-projected/sample;
 double requested=budget/lossPerLot;
 if(!MathIsValidNumber(requested)||requested<=0) return 0;
 PrintFormat("HOURLY_HISTORICAL_SIZE budget=%.2f historical_points=%.8f requested_lots=%.8f; NO SL, future loss can exceed reference",budget,H30_InpHistoricalLossPoints,requested);
 return requested;
}

void H30_Cycle(){
 if(H30_hourlyCycleBusy)return;H30_hourlyCycleBusy=true;datetime now=H30_UTC();H30_Mark();
 // Recover the scheduled exit from the broker position, not volatile RAM.
 for(int i=PositionsTotal()-1;i>=0;i--){ulong ticket=PositionGetTicket(i);if(!ticket||!H30_Own())continue;datetime entered=(datetime)PositionGetInteger(POSITION_TIME)-H30_Offset();MqlDateTime d;TimeToStruct(H30_NY(entered),d);int day=d.year*10000+d.mon*100+d.day;if(H30_lastDay[d.hour]!=day){H30_lastDay[d.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(H30_Key(d.hour),day);GlobalVariablesFlush();}}datetime expiry=(entered/60*60)+H30_InpHoldMinutes*60;if(now>=expiry&&now>=H30_closeRetry){H30_closeRetry=now+5;if(H30_Session(now+H30_Offset())){bool ok=H30_trade.PositionClose(ticket);uint rc=H30_trade.ResultRetcode();if(!ok||(rc!=TRADE_RETCODE_DONE&&rc!=TRADE_RETCODE_DONE_PARTIAL)){H30_closeFailures++;H30_closeRetry=now+30;Print("HOURLY_CLOSE_REJECT ",ticket," ",rc);}}}}
 MqlDateTime ny;TimeToStruct(H30_NY(now),ny);int day=ny.year*10000+ny.mon*100+ny.day;
 if(ny.day_of_week==0||ny.day_of_week==6||ny.min!=H30_InpEntryMinute||H30_directions[ny.hour]==0||H30_lastDay[ny.hour]==day){H30_hourlyCycleBusy=false;return;}
 MqlTick tick;if(!SymbolInfoTick(H30_Symbol,tick)||MathAbs((double)(tick.time-H30_Offset()-now))>3||tick.bid<=0||tick.ask<=0){H30_hourlyCycleBusy=false;return;}
 // Consume signal before any request: manual close/restart cannot re-enter it.
 H30_lastDay[ny.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(H30_Key(ny.hour),day);GlobalVariablesFlush();}
 if(H30_Owned()>0||!H30_Session(now+H30_Offset())){H30_blocked++;H30_hourlyCycleBusy=false;return;}
 double step=SymbolInfoDouble(H30_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(H30_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(H30_Symbol,SYMBOL_VOLUME_MAX);
 double requested=H30_HistoricalSizedLots(H30_directions[ny.hour],tick);
 if(!MathIsValidNumber(requested)||requested<=0||step<=0||lo<=0||hi<lo){H30_blocked++;H30_hourlyCycleBusy=false;return;}
 double lots=NormalizeDouble(lo+MathMax(0.0,MathFloor((requested-lo)/step+1e-10))*step,8);
 if(lots>hi){H30_blocked++;H30_hourlyCycleBusy=false;return;}
 if(lots>requested+1e-8)Print("HOURLY_MINIMUM_OVERRIDE requested=",requested," actual=",lots,"; historical scenario budget exceeded; NO loss cap");
 else if(MathAbs(lots-requested)>1e-8)Print("HOURLY_VOLUME_ROUNDED_DOWN requested=",requested," actual=",lots,"; NO future loss cap");
 MqlTradeRequest req;MqlTradeCheckResult check;ZeroMemory(req);ZeroMemory(check);req.action=TRADE_ACTION_DEAL;req.magic=H30_InpMagic;req.symbol=H30_Symbol;req.volume=lots;req.type=H30_directions[ny.hour]>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;req.price=H30_directions[ny.hour]>0?tick.ask:tick.bid;req.deviation=30;
 long fill=SymbolInfoInteger(H30_Symbol,SYMBOL_FILLING_MODE);req.type_filling=((fill&SYMBOL_FILLING_FOK)!=0)?ORDER_FILLING_FOK:(((fill&SYMBOL_FILLING_IOC)!=0)?ORDER_FILLING_IOC:ORDER_FILLING_RETURN);
 if(!OrderCheck(req,check)||(check.retcode!=0&&check.retcode!=TRADE_RETCODE_DONE)){H30_checksRejected++;Print("HOURLY_CHECK_REJECT ",check.retcode," ",check.comment);H30_hourlyCycleBusy=false;return;}
 H30_attempted++;string comment="NYH|"+IntegerToString(ny.hour)+"|"+IntegerToString(day);bool ok=H30_directions[ny.hour]>0?H30_trade.Buy(lots,H30_Symbol,0,0,0,comment):H30_trade.Sell(lots,H30_Symbol,0,0,0,comment);uint rc=H30_trade.ResultRetcode();
 if(ok&&(rc==TRADE_RETCODE_DONE||rc==TRADE_RETCODE_DONE_PARTIAL))H30_accepted++;else Print("HOURLY_ENTRY_REJECT ",ny.hour," ",rc,"; consumed, no blind retry");
 if(H30_fillFile!=INVALID_HANDLE)FileWrite(H30_fillFile,now,ny.hour,H30_directions[ny.hour],tick.bid,tick.ask,H30_trade.ResultPrice(),H30_trade.ResultDeal(),rc,lots);
 H30_hourlyCycleBusy=false;
}
int H30_OnInit(){
 if(H30_InpSizingMode<0||H30_InpSizingMode>2||!MathIsValidNumber(H30_InpRiskPercent)||H30_InpRiskPercent<=0||H30_InpRiskPercent>10||!MathIsValidNumber(H30_InpFixedRiskMoney)||H30_InpFixedRiskMoney<=0)return INIT_PARAMETERS_INCORRECT;
 if(H30_InpSizingMode!=0&&(!MathIsValidNumber(H30_InpHistoricalLossPoints)||H30_InpHistoricalLossPoints<=0))return INIT_PARAMETERS_INCORRECT;
 if(H30_InpLots<=0||H30_InpMagic<=0||H30_InpEntryMinute<0||H30_InpEntryMinute>59||H30_InpHoldMinutes<1||H30_InpHoldMinutes>180)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Separate position ownership requires a hedging account.");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL&&!H30_InpAllowRealAccount&&!MQLInfoInteger(MQL_TESTER)){Print("Research/demo default: real-account use disabled.");return INIT_FAILED;}
 ArrayInitialize(H30_directions,0);ArrayInitialize(H30_lastDay,0);int p=(int)H30_InpProfile;
 if(p==0){string s=H30_Symbol+" "+SymbolInfoString(H30_Symbol,SYMBOL_DESCRIPTION);StringToUpper(s);if(StringFind(s,"US30")>=0||StringFind(s,"WALL STREET")>=0||StringFind(s,"DJ30")>=0||StringFind(s,"DOW")>=0)p=1;else if(StringFind(s,"USTEC")>=0||StringFind(s,"US100")>=0||StringFind(s,"NASDAQ")>=0||StringFind(s,"US TECH")>=0)p=2;else if(StringFind(s,"US500")>=0||StringFind(s,"SP500")>=0||StringFind(s,"SPX500")>=0||StringFind(s,"S&P")>=0)p=3;else return INIT_PARAMETERS_INCORRECT;}
 string buy=H30_InpBuyHours,sell=H30_InpSellHours;if(buy==""&&sell==""){if(p==1){buy="2,6";sell="0,15,22";}else if(p==2){buy="2,13,20";sell="14,22";}else if(p==3){sell="22";}else return INIT_PARAMETERS_INCORRECT;}
 if(!H30_Parse(buy,1)||!H30_Parse(sell,-1))return INIT_PARAMETERS_INCORRECT;
 H30_prefix="NYH."+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"."+IntegerToString(H30_Hash(H30_Symbol+AccountInfoString(ACCOUNT_SERVER)+IntegerToString(H30_InpMagic)))+".";
 if(!MQLInfoInteger(MQL_TESTER))for(int h=0;h<24;h++)if(GlobalVariableCheck(H30_Key(h)))H30_lastDay[h]=(int)GlobalVariableGet(H30_Key(h));
 H30_trade.SetExpertMagicNumber(H30_InpMagic);H30_trade.SetDeviationInPoints(30);H30_trade.SetTypeFillingBySymbol(H30_Symbol);H30_trade.SetAsyncMode(false);
 H30_equityPeak=H30_minimumEquity=AccountInfoDouble(ACCOUNT_EQUITY);
 if(MQLInfoInteger(MQL_TESTER)){H30_curveFile=FileOpen(H30_InpAuditTag+"-curve.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');H30_fillFile=FileOpen(H30_InpAuditTag+"-fills.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(H30_curveFile==INVALID_HANDLE||H30_fillFile==INVALID_HANDLE)return INIT_FAILED;FileWrite(H30_curveFile,"utc_minute","balance_at_next_sample","equity_at_next_sample","minimum_equity","maximum_equity");FileWrite(H30_fillFile,"utc","ny_hour","side","bid","ask","fill_price","deal","retcode","lots");}
 Print("HOURLY_INIT profile=",p," BUY=",buy," SELL=",sell," sizingMode=",H30_InpSizingMode," historicalLossPoints=",H30_InpHistoricalLossPoints," riskPercent=",H30_InpRiskPercent," NO SL/TP; historical scenario, NOT a loss cap; server UTC offset=",H30_Offset());return INIT_SUCCEEDED;
}
void H30_OnTick(){H30_Cycle();}
void H30_OnTimer(){H30_Cycle();}
void H30_OnDeinit(const int reason){if(H30_curveFile!=INVALID_HANDLE){if(H30_curveMinute>0)FileWrite(H30_curveFile,H30_curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),H30_minuteMin,H30_minuteMax);FileClose(H30_curveFile);}if(H30_fillFile!=INVALID_HANDLE)FileClose(H30_fillFile);}
double H30_OnTester(){
 HistorySelect(0,TimeCurrent());int f=FileOpen(H30_InpAuditTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"ticket","position_id","time_msc","magic","entry","type","volume","price","profit","commission","swap","fee","comment");
 for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);if(HistoryDealGetInteger(d,DEAL_MAGIC)!=H30_InpMagic||HistoryDealGetString(d,DEAL_SYMBOL)!=H30_Symbol)continue;FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));}FileClose(f);
 H30_Mark();f=FileOpen(H30_InpAuditTag+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"attempted","accepted","blocked","checks_rejected","close_failures","max_equity_dd_pct","minimum_equity");FileWrite(f,H30_attempted,H30_accepted,H30_blocked,H30_checksRejected,H30_closeFailures,H30_maxEquityDD,H30_minimumEquity);FileClose(f);Print("HOURLY_COMPLETE attempted=",H30_attempted," accepted=",H30_accepted," blocked=",H30_blocked," checks=",H30_checksRejected," closeFailures=",H30_closeFailures);return 0;
}


const string H100_Symbol="USTEC";
const ENUM_TIMEFRAMES H100_Period=(ENUM_TIMEFRAMES)1;




enum H100_Profile { H100_AUTO_PROFILE=0, H100_US30_PROFILE=1, H100_US100_PROFILE=2, H100_SP500_PROFILE=3, H100_CUSTOM_PROFILE=4 };
const H100_Profile H100_InpProfile=(H100_Profile)2;
const string H100_InpBuyHours="";
const string H100_InpSellHours="";
const double H100_InpLots=1.0;
const int H100_InpSizingMode=1; // 0=frozen fixed lots, 1=balance percent, 2=fixed account cash
const double H100_InpRiskPercent=1.0;
const double H100_InpFixedRiskMoney=50.0;
const double H100_InpHistoricalLossPoints=358.71000;
const bool H100_InpAdaptivePortfolioControls=false;
const int H100_InpEntryMinute=0;
const int H100_InpHoldMinutes=60;
const long H100_InpMagic=104101001;
const bool H100_InpAllowRealAccount=false;
const bool H100_InpAutoServerUTC=true;
const int H100_InpServerUTCOffsetMinutes=0;
const string H100_InpAuditTag="five20261007-H100";
CTrade H100_trade;
int H100_directions[24], H100_lastDay[24];
string H100_prefix;
bool H100_hourlyCycleBusy=false;
datetime H100_closeRetry=0, H100_curveMinute=0;
double H100_equityPeak=0,H100_maxEquityDD=0,H100_minimumEquity=0,H100_minuteMin=0,H100_minuteMax=0;
int H100_curveFile=INVALID_HANDLE,H100_fillFile=INVALID_HANDLE;
int H100_attempted=0,H100_accepted=0,H100_blocked=0,H100_closeFailures=0,H100_checksRejected=0;

int H100_Sunday(int y,int m,int n){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=1;TimeToStruct(StructToTime(x),x);return 1+(7-x.day_of_week)%7+7*(n-1);}
datetime H100_NY(datetime utc){MqlDateTime x,a,b;TimeToStruct(utc,x);ZeroMemory(a);ZeroMemory(b);a.year=x.year;a.mon=3;a.day=H100_Sunday(x.year,3,2);a.hour=7;b.year=x.year;b.mon=11;b.day=H100_Sunday(x.year,11,1);b.hour=6;return utc-((utc>=StructToTime(a)&&utc<StructToTime(b))?4:5)*3600;}
int H100_Offset(){if(MQLInfoInteger(MQL_TESTER)||!H100_InpAutoServerUTC)return H100_InpServerUTCOffsetMinutes*60;return (int)MathRound((double)(TimeTradeServer()-TimeGMT())/900.)*900;}
datetime H100_UTC(){return (MQLInfoInteger(MQL_TESTER)?TimeCurrent():TimeTradeServer())-H100_Offset();}
uint H100_Hash(string s){uint v=2166136261;for(int i=0;i<StringLen(s);i++){v^=(uint)StringGetCharacter(s,i);v*=16777619;}return v;}
string H100_Key(int h){return H100_prefix+IntegerToString(h);}
bool H100_Parse(string text,int side){if(text=="")return true;string a[];int n=StringSplit(text,',',a);for(int i=0;i<n;i++){StringTrimLeft(a[i]);StringTrimRight(a[i]);int h=(int)StringToInteger(a[i]);if(h<0||h>23||IntegerToString(h)!=a[i]||(H100_directions[h]!=0&&H100_directions[h]!=side))return false;H100_directions[h]=side;}return true;}
bool H100_Own(){return PositionGetString(POSITION_SYMBOL)==H100_Symbol&&PositionGetInteger(POSITION_MAGIC)==H100_InpMagic;}
int H100_Owned(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0&&H100_Own())n++;return n;}
bool H100_Session(datetime server){MqlDateTime d;TimeToStruct(server,d);int sec=d.hour*3600+d.min*60+d.sec;datetime a,b;bool known=false;for(uint i=0;i<20;i++){if(!SymbolInfoSessionTrade(H100_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;known=true;int from=(int)a%86400,to=(int)b%86400;if(from==to||(from<to&&sec>=from&&sec<to)||(from>to&&(sec>=from||sec<to)))return true;}return !known;}
void H100_Mark(){if(!MQLInfoInteger(MQL_TESTER))return;double e=AccountInfoDouble(ACCOUNT_EQUITY);H100_equityPeak=MathMax(H100_equityPeak,e);H100_minimumEquity=MathMin(H100_minimumEquity,e);if(H100_equityPeak>0)H100_maxEquityDD=MathMax(H100_maxEquityDD,100*(H100_equityPeak-e)/H100_equityPeak);datetime m=H100_UTC()/60*60;if(H100_curveMinute!=m){if(H100_curveMinute>0)FileWrite(H100_curveFile,H100_curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),e,H100_minuteMin,H100_minuteMax);H100_curveMinute=m;H100_minuteMin=e;H100_minuteMax=e;}else{H100_minuteMin=MathMin(H100_minuteMin,e);H100_minuteMax=MathMax(H100_minuteMax,e);}}

double H100_HistoricalSizedLots(const int side,const MqlTick &tick)
{
 if(H100_InpSizingMode==0) return H100_InpLots; // Exact frozen fixed-lot benchmark.
 double multiplier=CalyxAdaptiveRiskMultiplier(H100_InpAdaptivePortfolioControls,H100_InpMagic);
 if(multiplier<=0) return 0;
 double budget=(H100_InpSizingMode==2 ? H100_InpFixedRiskMoney : AccountInfoDouble(ACCOUNT_BALANCE)*H100_InpRiskPercent/100.0)*multiplier;
 double sample=MathMax(SymbolInfoDouble(H100_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(H100_Symbol,SYMBOL_VOLUME_STEP));
 double tickSize=SymbolInfoDouble(H100_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double price=(side>0 ? tick.ask : tick.bid);
 if(!MathIsValidNumber(budget)||budget<=0||sample<=0||tickSize<=0) return 0;
 // The reference includes historical net costs expressed in index price units.
 // It is a synthetic adverse move for sizing, NOT a placed protective stop.
 double distance=MathCeil(H100_InpHistoricalLossPoints/tickSize)*tickSize;
 double exitPrice=NormalizeDouble(price+(side>0 ? -distance : distance),((int)SymbolInfoInteger(H100_Symbol,SYMBOL_DIGITS)));
 double projected=0;
 if(exitPrice<=0||!OrderCalcProfit(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,H100_Symbol,sample,price,exitPrice,projected)||!MathIsValidNumber(projected)||projected>=0) return 0;
 double lossPerLot=-projected/sample;
 double requested=budget/lossPerLot;
 if(!MathIsValidNumber(requested)||requested<=0) return 0;
 PrintFormat("HOURLY_HISTORICAL_SIZE budget=%.2f historical_points=%.8f requested_lots=%.8f; NO SL, future loss can exceed reference",budget,H100_InpHistoricalLossPoints,requested);
 return requested;
}

void H100_Cycle(){
 if(H100_hourlyCycleBusy)return;H100_hourlyCycleBusy=true;datetime now=H100_UTC();H100_Mark();
 // Recover the scheduled exit from the broker position, not volatile RAM.
 for(int i=PositionsTotal()-1;i>=0;i--){ulong ticket=PositionGetTicket(i);if(!ticket||!H100_Own())continue;datetime entered=(datetime)PositionGetInteger(POSITION_TIME)-H100_Offset();MqlDateTime d;TimeToStruct(H100_NY(entered),d);int day=d.year*10000+d.mon*100+d.day;if(H100_lastDay[d.hour]!=day){H100_lastDay[d.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(H100_Key(d.hour),day);GlobalVariablesFlush();}}datetime expiry=(entered/60*60)+H100_InpHoldMinutes*60;if(now>=expiry&&now>=H100_closeRetry){H100_closeRetry=now+5;if(H100_Session(now+H100_Offset())){bool ok=H100_trade.PositionClose(ticket);uint rc=H100_trade.ResultRetcode();if(!ok||(rc!=TRADE_RETCODE_DONE&&rc!=TRADE_RETCODE_DONE_PARTIAL)){H100_closeFailures++;H100_closeRetry=now+30;Print("HOURLY_CLOSE_REJECT ",ticket," ",rc);}}}}
 MqlDateTime ny;TimeToStruct(H100_NY(now),ny);int day=ny.year*10000+ny.mon*100+ny.day;
 if(ny.day_of_week==0||ny.day_of_week==6||ny.min!=H100_InpEntryMinute||H100_directions[ny.hour]==0||H100_lastDay[ny.hour]==day){H100_hourlyCycleBusy=false;return;}
 MqlTick tick;if(!SymbolInfoTick(H100_Symbol,tick)||MathAbs((double)(tick.time-H100_Offset()-now))>3||tick.bid<=0||tick.ask<=0){H100_hourlyCycleBusy=false;return;}
 // Consume signal before any request: manual close/restart cannot re-enter it.
 H100_lastDay[ny.hour]=day;if(!MQLInfoInteger(MQL_TESTER)){GlobalVariableSet(H100_Key(ny.hour),day);GlobalVariablesFlush();}
 if(H100_Owned()>0||!H100_Session(now+H100_Offset())){H100_blocked++;H100_hourlyCycleBusy=false;return;}
 double step=SymbolInfoDouble(H100_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(H100_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(H100_Symbol,SYMBOL_VOLUME_MAX);
 double requested=H100_HistoricalSizedLots(H100_directions[ny.hour],tick);
 if(!MathIsValidNumber(requested)||requested<=0||step<=0||lo<=0||hi<lo){H100_blocked++;H100_hourlyCycleBusy=false;return;}
 double lots=NormalizeDouble(lo+MathMax(0.0,MathFloor((requested-lo)/step+1e-10))*step,8);
 if(lots>hi){H100_blocked++;H100_hourlyCycleBusy=false;return;}
 if(lots>requested+1e-8)Print("HOURLY_MINIMUM_OVERRIDE requested=",requested," actual=",lots,"; historical scenario budget exceeded; NO loss cap");
 else if(MathAbs(lots-requested)>1e-8)Print("HOURLY_VOLUME_ROUNDED_DOWN requested=",requested," actual=",lots,"; NO future loss cap");
 MqlTradeRequest req;MqlTradeCheckResult check;ZeroMemory(req);ZeroMemory(check);req.action=TRADE_ACTION_DEAL;req.magic=H100_InpMagic;req.symbol=H100_Symbol;req.volume=lots;req.type=H100_directions[ny.hour]>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;req.price=H100_directions[ny.hour]>0?tick.ask:tick.bid;req.deviation=30;
 long fill=SymbolInfoInteger(H100_Symbol,SYMBOL_FILLING_MODE);req.type_filling=((fill&SYMBOL_FILLING_FOK)!=0)?ORDER_FILLING_FOK:(((fill&SYMBOL_FILLING_IOC)!=0)?ORDER_FILLING_IOC:ORDER_FILLING_RETURN);
 if(!OrderCheck(req,check)||(check.retcode!=0&&check.retcode!=TRADE_RETCODE_DONE)){H100_checksRejected++;Print("HOURLY_CHECK_REJECT ",check.retcode," ",check.comment);H100_hourlyCycleBusy=false;return;}
 H100_attempted++;string comment="NYH|"+IntegerToString(ny.hour)+"|"+IntegerToString(day);bool ok=H100_directions[ny.hour]>0?H100_trade.Buy(lots,H100_Symbol,0,0,0,comment):H100_trade.Sell(lots,H100_Symbol,0,0,0,comment);uint rc=H100_trade.ResultRetcode();
 if(ok&&(rc==TRADE_RETCODE_DONE||rc==TRADE_RETCODE_DONE_PARTIAL))H100_accepted++;else Print("HOURLY_ENTRY_REJECT ",ny.hour," ",rc,"; consumed, no blind retry");
 if(H100_fillFile!=INVALID_HANDLE)FileWrite(H100_fillFile,now,ny.hour,H100_directions[ny.hour],tick.bid,tick.ask,H100_trade.ResultPrice(),H100_trade.ResultDeal(),rc,lots);
 H100_hourlyCycleBusy=false;
}
int H100_OnInit(){
 if(H100_InpSizingMode<0||H100_InpSizingMode>2||!MathIsValidNumber(H100_InpRiskPercent)||H100_InpRiskPercent<=0||H100_InpRiskPercent>10||!MathIsValidNumber(H100_InpFixedRiskMoney)||H100_InpFixedRiskMoney<=0)return INIT_PARAMETERS_INCORRECT;
 if(H100_InpSizingMode!=0&&(!MathIsValidNumber(H100_InpHistoricalLossPoints)||H100_InpHistoricalLossPoints<=0))return INIT_PARAMETERS_INCORRECT;
 if(H100_InpLots<=0||H100_InpMagic<=0||H100_InpEntryMinute<0||H100_InpEntryMinute>59||H100_InpHoldMinutes<1||H100_InpHoldMinutes>180)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Separate position ownership requires a hedging account.");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL&&!H100_InpAllowRealAccount&&!MQLInfoInteger(MQL_TESTER)){Print("Research/demo default: real-account use disabled.");return INIT_FAILED;}
 ArrayInitialize(H100_directions,0);ArrayInitialize(H100_lastDay,0);int p=(int)H100_InpProfile;
 if(p==0){string s=H100_Symbol+" "+SymbolInfoString(H100_Symbol,SYMBOL_DESCRIPTION);StringToUpper(s);if(StringFind(s,"US30")>=0||StringFind(s,"WALL STREET")>=0||StringFind(s,"DJ30")>=0||StringFind(s,"DOW")>=0)p=1;else if(StringFind(s,"USTEC")>=0||StringFind(s,"US100")>=0||StringFind(s,"NASDAQ")>=0||StringFind(s,"US TECH")>=0)p=2;else if(StringFind(s,"US500")>=0||StringFind(s,"SP500")>=0||StringFind(s,"SPX500")>=0||StringFind(s,"S&P")>=0)p=3;else return INIT_PARAMETERS_INCORRECT;}
 string buy=H100_InpBuyHours,sell=H100_InpSellHours;if(buy==""&&sell==""){if(p==1){buy="2,6";sell="0,15,22";}else if(p==2){buy="2,13,20";sell="14,22";}else if(p==3){sell="22";}else return INIT_PARAMETERS_INCORRECT;}
 if(!H100_Parse(buy,1)||!H100_Parse(sell,-1))return INIT_PARAMETERS_INCORRECT;
 H100_prefix="NYH."+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"."+IntegerToString(H100_Hash(H100_Symbol+AccountInfoString(ACCOUNT_SERVER)+IntegerToString(H100_InpMagic)))+".";
 if(!MQLInfoInteger(MQL_TESTER))for(int h=0;h<24;h++)if(GlobalVariableCheck(H100_Key(h)))H100_lastDay[h]=(int)GlobalVariableGet(H100_Key(h));
 H100_trade.SetExpertMagicNumber(H100_InpMagic);H100_trade.SetDeviationInPoints(30);H100_trade.SetTypeFillingBySymbol(H100_Symbol);H100_trade.SetAsyncMode(false);
 H100_equityPeak=H100_minimumEquity=AccountInfoDouble(ACCOUNT_EQUITY);
 if(MQLInfoInteger(MQL_TESTER)){H100_curveFile=FileOpen(H100_InpAuditTag+"-curve.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');H100_fillFile=FileOpen(H100_InpAuditTag+"-fills.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(H100_curveFile==INVALID_HANDLE||H100_fillFile==INVALID_HANDLE)return INIT_FAILED;FileWrite(H100_curveFile,"utc_minute","balance_at_next_sample","equity_at_next_sample","minimum_equity","maximum_equity");FileWrite(H100_fillFile,"utc","ny_hour","side","bid","ask","fill_price","deal","retcode","lots");}
 Print("HOURLY_INIT profile=",p," BUY=",buy," SELL=",sell," sizingMode=",H100_InpSizingMode," historicalLossPoints=",H100_InpHistoricalLossPoints," riskPercent=",H100_InpRiskPercent," NO SL/TP; historical scenario, NOT a loss cap; server UTC offset=",H100_Offset());return INIT_SUCCEEDED;
}
void H100_OnTick(){H100_Cycle();}
void H100_OnTimer(){H100_Cycle();}
void H100_OnDeinit(const int reason){if(H100_curveFile!=INVALID_HANDLE){if(H100_curveMinute>0)FileWrite(H100_curveFile,H100_curveMinute,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),H100_minuteMin,H100_minuteMax);FileClose(H100_curveFile);}if(H100_fillFile!=INVALID_HANDLE)FileClose(H100_fillFile);}
double H100_OnTester(){
 HistorySelect(0,TimeCurrent());int f=FileOpen(H100_InpAuditTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"ticket","position_id","time_msc","magic","entry","type","volume","price","profit","commission","swap","fee","comment");
 for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);if(HistoryDealGetInteger(d,DEAL_MAGIC)!=H100_InpMagic||HistoryDealGetString(d,DEAL_SYMBOL)!=H100_Symbol)continue;FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));}FileClose(f);
 H100_Mark();f=FileOpen(H100_InpAuditTag+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(f,"attempted","accepted","blocked","checks_rejected","close_failures","max_equity_dd_pct","minimum_equity");FileWrite(f,H100_attempted,H100_accepted,H100_blocked,H100_checksRejected,H100_closeFailures,H100_maxEquityDD,H100_minimumEquity);FileClose(f);Print("HOURLY_COMPLETE attempted=",H100_attempted," accepted=",H100_accepted," blocked=",H100_blocked," checks=",H100_checksRejected," closeFailures=",H100_closeFailures);return 0;
}


const string N5_Symbol="USTEC";
const ENUM_TIMEFRAMES N5_Period=(ENUM_TIMEFRAMES)5;



// Research copy 2026-09-25 of Nasdaq 5M Candle Momentum DI EA v2.10 (production source unchanged).
// Adds, default OFF: N5_STOP_PERCENT initial stop and slow-MA trailing, to recreate the management seen in the
// user's QUANT_LAB "Momentum v2.0" video (0.60% stop, no target, stop trailed on a slow MA, held overnight).

#define N5_HAMA_PER_EA_SAFE_REGIME_FILTER_MQH

// This gate is compiled into each EA that includes this file. It has no
// account-wide state and cannot approve or reject another EA's trades.
const bool N5_InpUseMarkovRegimeFilter=false;
const int N5_InpMarkovReturnWindow=40;
const double N5_InpMarkovThreshold=0.05;
const double N5_InpMarkovSignalGate=0.05;
const int N5_InpMarkovMinLabels=252;
const int N5_InpMarkovHistoryBars=2600;

int N5_HAMA_SafeRegimeStateAt(double &closes[],const int index)
{
   double older=closes[index+N5_InpMarkovReturnWindow];
   if(older<=0.0) return 1;
   double rolling_return=closes[index]/older-1.0;
   if(rolling_return>N5_InpMarkovThreshold) return 2;
   if(rolling_return<-N5_InpMarkovThreshold) return 0;
   return 1;
}

bool N5_HAMA_SafeRegimeAllowsDirection(const int direction)
{
   if(!N5_InpUseMarkovRegimeFilter) return true;
   int available=Bars(N5_Symbol,PERIOD_D1)-1;
   int requested=MathMin(N5_InpMarkovHistoryBars,available);
   if(requested<=N5_InpMarkovReturnWindow+N5_InpMarkovMinLabels) return false;

   double closes[];
   ArraySetAsSeries(closes,true);
   int copied=CopyClose(N5_Symbol,PERIOD_D1,1,requested,closes);
   int labels=copied-N5_InpMarkovReturnWindow;
   if(labels<=N5_InpMarkovMinLabels) return false;

   double counts[3][3];
   for(int row=0;row<3;row++)
      for(int col=0;col<3;col++) counts[row][col]=0.0;

   // The newest completed D1 label is used only as the forecast state. The
   // transition into it is excluded, matching the no-lookahead research.
   int oldest=labels-1;
   for(int newer=oldest-1;newer>=1;newer--)
   {
      int from=N5_HAMA_SafeRegimeStateAt(closes,newer+1);
      int to=N5_HAMA_SafeRegimeStateAt(closes,newer);
      counts[from][to]+=1.0;
   }

   int state=N5_HAMA_SafeRegimeStateAt(closes,0);
   double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0) return false;
   double signal=(counts[state][2]-counts[state][0])/total;
   return (direction>0 ? signal>N5_InpMarkovSignalGate : signal<-N5_InpMarkovSignalGate);
}



#define N5_DYNAMIC_TRAILING_SESSION_FILTER_MQH

enum N5_ENUM_DTS_SESSION_MODE
  {
   N5_DTS_SESSION_ALL=0,
   N5_DTS_SESSION_ASIA=1,
   N5_DTS_SESSION_LONDON=2,
   N5_DTS_SESSION_NEW_YORK=3,
   N5_DTS_SESSION_LONDON_NEW_YORK_OVERLAP=4
  };
const bool N5_InpUseDynamicTrailingSL=false;
const double N5_InpDynamicTriggerFraction=0.50;
const double N5_InpDynamicLockFraction=0.20;
const N5_ENUM_DTS_SESSION_MODE N5_InpResearchSession=(N5_ENUM_DTS_SESSION_MODE)0;
const int N5_InpResearchBrokerUtcOffsetMinutes=0;

struct N5_DTS_TRACKED_POSITION
  {
   ulong    identifier;
   datetime opened;
   double   target_distance;
  };

N5_DTS_TRACKED_POSITION N5_g_dts_positions[];
datetime N5_g_dts_last_m15_bar=0;

bool N5_DTS_InputsValid()
  {
   return N5_InpDynamicTriggerFraction>0.0 && N5_InpDynamicTriggerFraction<=1.0 &&
          N5_InpDynamicLockFraction>=0.0 && N5_InpDynamicLockFraction<N5_InpDynamicTriggerFraction &&
          N5_InpResearchBrokerUtcOffsetMinutes>=-840 && N5_InpResearchBrokerUtcOffsetMinutes<=840;
  }

bool N5_DTS_MinuteInside(const int minute_of_day,const int start_minute,const int end_minute)
  {
   if(start_minute==end_minute) return true;
   if(start_minute<end_minute) return minute_of_day>=start_minute && minute_of_day<end_minute;
   return minute_of_day>=start_minute || minute_of_day<end_minute;
  }

bool N5_DTS_EntrySessionAllowed()
  {
   if(N5_InpResearchSession==N5_DTS_SESSION_ALL) return true;
   datetime utc=TimeCurrent()-N5_InpResearchBrokerUtcOffsetMinutes*60;
   MqlDateTime now; TimeToStruct(utc,now);
   int minute_of_day=now.hour*60+now.min;
   if(N5_InpResearchSession==N5_DTS_SESSION_ASIA)
      return N5_DTS_MinuteInside(minute_of_day,0,8*60);
   if(N5_InpResearchSession==N5_DTS_SESSION_LONDON)
      return N5_DTS_MinuteInside(minute_of_day,7*60,12*60);
   if(N5_InpResearchSession==N5_DTS_SESSION_NEW_YORK)
      return N5_DTS_MinuteInside(minute_of_day,13*60,21*60);
   if(N5_InpResearchSession==N5_DTS_SESSION_LONDON_NEW_YORK_OVERLAP)
      return N5_DTS_MinuteInside(minute_of_day,13*60,16*60);
   return true;
  }

int N5_DTS_FindTracked(const ulong identifier)
  {
   for(int i=0;i<ArraySize(N5_g_dts_positions);i++)
      if(N5_g_dts_positions[i].identifier==identifier) return i;
   return -1;
  }

void N5_DTS_ObservePositions(const long magic)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=N5_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(N5_DTS_FindTracked(identifier)>=0) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double target=PositionGetDouble(POSITION_TP);
      double stop=PositionGetDouble(POSITION_SL);
      double distance=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(target>entry) distance=target-entry;
         else if(stop>0.0 && stop<entry) distance=entry-stop;
        }
      else
        {
         if(target>0.0 && target<entry) distance=entry-target;
         else if(stop>entry) distance=stop-entry;
        }
      if(distance<=SymbolInfoDouble(N5_Symbol,SYMBOL_POINT)) continue;
      int size=ArraySize(N5_g_dts_positions);
      ArrayResize(N5_g_dts_positions,size+1);
      N5_g_dts_positions[size].identifier=identifier;
      N5_g_dts_positions[size].opened=(datetime)PositionGetInteger(POSITION_TIME);
      N5_g_dts_positions[size].target_distance=distance;
     }
  }

bool N5_DTS_ModifyStop(const ulong ticket,const double stop,const double target)
  {
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.symbol=N5_Symbol;
   request.sl=NormalizeDouble(stop,(int)SymbolInfoInteger(N5_Symbol,SYMBOL_DIGITS));
   request.tp=target;
   if(!OrderSend(request,result)) return false;
   return result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED || result.retcode==TRADE_RETCODE_NO_CHANGES;
  }

void N5_DTS_ManageDynamicTrailing(const long magic)
  {
   if(!N5_InpUseDynamicTrailingSL) return;
   N5_DTS_ObservePositions(magic);
   datetime current_m15=iTime(N5_Symbol,PERIOD_M15,0);
   if(current_m15<=0) return;
   if(N5_g_dts_last_m15_bar==0)
     {
      N5_g_dts_last_m15_bar=current_m15;
      return;
     }
   if(current_m15==N5_g_dts_last_m15_bar) return;
   N5_g_dts_last_m15_bar=current_m15;
   double closed_price=iClose(N5_Symbol,PERIOD_M15,1);
   if(closed_price<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(N5_Symbol,tick)) return;
   double point=SymbolInfoDouble(N5_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax(point,SymbolInfoInteger(N5_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=N5_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      int tracked=N5_DTS_FindTracked(identifier);
      if(tracked<0 || N5_g_dts_positions[tracked].target_distance<=point) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double distance=N5_g_dts_positions[tracked].target_distance;
      double desired=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(closed_price<entry+N5_InpDynamicTriggerFraction*distance) continue;
         desired=entry+N5_InpDynamicLockFraction*distance;
         desired=MathMin(desired,tick.bid-broker_gap);
         if(desired<=entry || (current_stop>0.0 && desired<=current_stop+point)) continue;
        }
      else
        {
         if(closed_price>entry-N5_InpDynamicTriggerFraction*distance) continue;
         desired=entry-N5_InpDynamicLockFraction*distance;
         desired=MathMax(desired,tick.ask+broker_gap);
         if(desired>=entry || (current_stop>0.0 && desired>=current_stop-point)) continue;
        }
      if(!N5_DTS_ModifyStop(ticket,desired,target))
         Print("Dynamic trailing SL modification failed for position ",ticket);
     }
  }



enum N5_ENUM_N5_STOP_MODE
  {
   N5_N5_STOP_ATR=0,
   N5_N5_STOP_SIGNAL_CANDLE=1,
   N5_N5_STOP_PERCENT=2
  };
const ENUM_TIMEFRAMES N5_InpSignalTimeframe=(ENUM_TIMEFRAMES)5;
const int N5_InpSignalHourNY=9;
const int N5_InpSignalMinuteNY=30;
const int N5_InpEMAPeriod=12;
const bool N5_InpAllowLong=true;
const bool N5_InpAllowShort=true;
const bool N5_InpRequireEMASlope=false;
const double N5_InpMinimumBodyATR=0.0;
const double N5_InpMaximumBodyATR=0.0;
const double N5_InpMinimumBodyFraction=0.0;
const double N5_InpMinimumEMADistanceATR=0.0;
const double N5_InpMaximumEMADistanceATR=0.0;
const int N5_InpRelativeVolumePeriod=0;
const double N5_InpMinimumRelativeVolume=0.0;
const bool N5_InpRequireDIAgreement=true; // true: longs need +DI>-DI, shorts need -DI>+DI on the closed signal bar
const int N5_InpDIPeriod=14;
const int N5_InpATRPeriod=14;
const N5_ENUM_N5_STOP_MODE N5_InpStopMode=(N5_ENUM_N5_STOP_MODE)2;
const double N5_InpInitialStopATR=4.0;
const double N5_InpSignalStopBufferATR=0.10;
const double N5_InpMaximumStopATR=0.0;
const bool N5_InpUseFixedTarget=false;
const double N5_InpRewardRisk=2.5;
const bool N5_InpUseAdaptiveRR=false;
const double N5_InpAdaptiveStrongBodyATR=1.0;
const double N5_InpAdaptiveStrongRR=3.0;
const double N5_InpInitialStopPercent=0.60;   // used only by N5_STOP_PERCENT (percent of entry price)
const bool N5_InpUseATRTrailing=true;
const double N5_InpTrailingATR=6.0;
const double N5_InpTrailStartR=1.0;
const bool N5_InpUseBreakEven=false;
const double N5_InpBreakEvenTriggerR=1.0;
const double N5_InpBreakEvenLockR=0.0;
const int N5_InpMaximumHoldingMinutes=0;
const bool N5_InpCloseAtSessionEnd=false;
const int N5_InpCloseHourNY=15;
const int N5_InpCloseMinuteNY=55;
const bool N5_InpUseMATrailing=false;        // research: stop follows a slow MA (closed bar), never loosened
const int N5_InpTrailMAPeriod=200;
const ENUM_MA_METHOD N5_InpTrailMAMethod=(ENUM_MA_METHOD)MODE_EMA;
const double N5_InpTrailMAStartR=0.50;         // start trailing once open profit >= this many R
const bool N5_InpAutoServerUtcOffsetLive=true;
const int N5_InpServerUtcOffsetHours=0;
const bool N5_InpEnableTrading=true;
const double N5_InpRiskPercent=1.0;
const bool N5_InpAdaptivePortfolioControls=false;
const double N5_InpMaximumSpreadATR=0.0;
const long N5_InpMagic=862020;
const int N5_InpMaximumDeviationPoints=50;

CTrade N5_g_trade;
int N5_g_ema_handle=INVALID_HANDLE;
int N5_g_atr_handle=INVALID_HANDLE;
int N5_g_adx_handle=INVALID_HANDLE;
int N5_g_trail_ma_handle=INVALID_HANDLE;
datetime N5_g_last_bar_time=0;

double N5_NormalizePrice(const double price)
  {
   return NormalizeDouble(price,(int)SymbolInfoInteger(N5_Symbol,SYMBOL_DIGITS));
  }

double N5_NormalizeLots(const double raw_lots)
  {
   double minimum=SymbolInfoDouble(N5_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(N5_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(N5_Symbol,SYMBOL_VOLUME_STEP);
   if(raw_lots<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw_lots,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   if(lots>raw_lots+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw_lots,lots);
   return lots;
  }

double N5_LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
  {
   // The research executable is hard-capped at one percent per trade.
   double applied_risk=MathMin(N5_InpRiskPercent,1.00);
   const double adaptive=CalyxAdaptiveRiskMultiplier(N5_InpAdaptivePortfolioControls,N5_InpMagic);
   if(adaptive<=0.0) return 0.0;
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*applied_risk*adaptive/100.0;
   double one_lot=0.0;
   if(cash<=0.0 || !OrderCalcProfit(type,N5_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   return N5_NormalizeLots(cash/one_lot);
  }

bool N5_ReadIndicatorValue(const int handle,const int shift,double &value)
  {
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
  }

int N5_ServerUtcOffsetSeconds()
  {
   if(!N5_InpAutoServerUtcOffsetLive || (bool)MQLInfoInteger(MQL_TESTER))
      return N5_InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer();
   datetime utc=TimeGMT();
   if(server<=0 || utc<=0) return N5_InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
  }

datetime N5_BuildUtcTime(const int year,const int month,const int day,const int hour)
  {
   MqlDateTime value;
   ZeroMemory(value);
   value.year=year;
   value.mon=month;
   value.day=day;
   value.hour=hour;
   return StructToTime(value);
  }

int N5_NthSunday(const int year,const int month,const int nth)
  {
   MqlDateTime first;
   TimeToStruct(N5_BuildUtcTime(year,month,1,0),first);
   int first_sunday=1+((7-first.day_of_week)%7);
   return first_sunday+(nth-1)*7;
  }

int N5_NewYorkUtcOffsetHours(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime dst_start=N5_BuildUtcTime(parts.year,3,N5_NthSunday(parts.year,3,2),7);
   datetime dst_end=N5_BuildUtcTime(parts.year,11,N5_NthSunday(parts.year,11,1),6);
   return (utc_time>=dst_start && utc_time<dst_end ? -4 : -5);
  }

datetime N5_ServerToNewYork(const datetime server_time)
  {
   datetime utc_time=server_time-N5_ServerUtcOffsetSeconds();
   return utc_time+N5_NewYorkUtcOffsetHours(utc_time)*3600;
  }

int N5_NewYorkDateKey(const datetime server_time)
  {
   MqlDateTime ny;
   TimeToStruct(N5_ServerToNewYork(server_time),ny);
   return ny.year*10000+ny.mon*100+ny.day;
  }

bool N5_IsNewYorkTime(const datetime server_time,const int hour,const int minute)
  {
   MqlDateTime ny;
   TimeToStruct(N5_ServerToNewYork(server_time),ny);
   return ny.day_of_week>=1 && ny.day_of_week<=5 && ny.hour==hour && ny.min==minute;
  }

bool N5_IsAtOrAfterSessionClose(const datetime server_time)
  {
   MqlDateTime ny;
   TimeToStruct(N5_ServerToNewYork(server_time),ny);
   if(ny.day_of_week<1 || ny.day_of_week>5) return false;
   return ny.hour>N5_InpCloseHourNY || (ny.hour==N5_InpCloseHourNY && ny.min>=N5_InpCloseMinuteNY);
  }

bool N5_IsOurPosition()
  {
   return PositionGetString(POSITION_SYMBOL)==N5_Symbol && PositionGetInteger(POSITION_MAGIC)==N5_InpMagic;
  }

bool N5_SelectOurPosition(ulong &ticket)
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ticket=PositionGetTicket(index);
      if(ticket>0 && N5_IsOurPosition()) return true;
     }
   ticket=0;
   return false;
  }

string N5_RiskKey(const ulong identifier)
  {
   return "N5EMA."+(string)N5_InpMagic+"."+(string)identifier+".R";
  }

void N5_StoreInitialRisk()
  {
   ulong ticket=0;
   if(!N5_SelectOurPosition(ticket)) return;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   double risk=MathAbs(open-stop);
   if(identifier>0 && risk>0.0) GlobalVariableSet(N5_RiskKey(identifier),risk);
  }

double N5_InitialRiskForSelectedPosition()
  {
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string key=N5_RiskKey(identifier);
   if(identifier>0 && GlobalVariableCheck(key))
     {
      double stored=GlobalVariableGet(key);
      if(stored>0.0) return stored;
     }
   return MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
  }

bool N5_AlreadyTradedOnNewYorkDate(const int date_key)
  {
   datetime now=TimeCurrent();
   if(!HistorySelect(now-4*86400,now+3600)) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
     {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0) continue;
      if(HistoryDealGetInteger(deal,DEAL_MAGIC)!=N5_InpMagic) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=N5_Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT) continue;
      datetime when=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      if(N5_NewYorkDateKey(when)==date_key) return true;
     }
   return false;
  }

bool N5_CurrentSpreadPasses(const double atr)
  {
   if(N5_InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(N5_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=N5_InpMaximumSpreadATR*atr;
  }

double N5_RelativeVolume(const int signal_shift)
  {
   if(N5_InpRelativeVolumePeriod<2) return 999.0;
   long signal_volume=iVolume(N5_Symbol,N5_InpSignalTimeframe,signal_shift);
   if(signal_volume<=0) return 0.0;
   double total=0.0;
   int valid=0;
   for(int shift=signal_shift+1;shift<=signal_shift+N5_InpRelativeVolumePeriod;shift++)
     {
      long volume=iVolume(N5_Symbol,N5_InpSignalTimeframe,shift);
      if(volume<=0) continue;
      total+=(double)volume;
      valid++;
     }
   if(valid<N5_InpRelativeVolumePeriod/2 || total<=0.0) return 0.0;
   return (double)signal_volume/(total/valid);
  }

double N5_SelectedRewardRisk(const MqlRates &signal,const double atr)
  {
   if(!N5_InpUseAdaptiveRR || atr<=0.0) return N5_InpRewardRisk;
   double body=MathAbs(signal.close-signal.open)/atr;
   return (body>=N5_InpAdaptiveStrongBodyATR ? N5_InpAdaptiveStrongRR : N5_InpRewardRisk);
  }

bool N5_SendEntry(const int direction,const double atr,const MqlRates &signal,const double reward_risk)
  {
   if(!N5_DTS_EntrySessionAllowed()) return false;
   if(!N5_HAMA_SafeRegimeAllowsDirection(direction)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(N5_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(N5_InpStopMode==N5_N5_STOP_SIGNAL_CANDLE
                ? (direction>0 ? signal.low-N5_InpSignalStopBufferATR*atr : signal.high+N5_InpSignalStopBufferATR*atr)
                : entry-direction*N5_InpInitialStopATR*atr);
   if(N5_InpStopMode==N5_N5_STOP_PERCENT)
      stop=entry-direction*entry*N5_InpInitialStopPercent/100.0;
   if(N5_InpMaximumStopATR>0.0 && MathAbs(entry-stop)>N5_InpMaximumStopATR*atr)
      stop=entry-direction*N5_InpMaximumStopATR*atr;
   stop=N5_NormalizePrice(stop);
   double point=SymbolInfoDouble(N5_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(N5_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(N5_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && stop>=entry-broker_gap) stop=N5_NormalizePrice(entry-broker_gap);
   if(direction<0 && stop<=entry+broker_gap) stop=N5_NormalizePrice(entry+broker_gap);
   double risk=MathAbs(entry-stop);
   double target=0.0;
   if(N5_InpUseFixedTarget)
     {
      target=N5_NormalizePrice(entry+direction*reward_risk*risk);
      if(MathAbs(target-entry)<broker_gap) target=N5_NormalizePrice(entry+direction*broker_gap);
     }
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=N5_LotsForRisk(type,entry,stop);
   if(lots<=0.0)
     {
      Print("N5EMA skipped: risk-sized volume is below the broker minimum.");
      return false;
     }
   N5_g_trade.SetExpertMagicNumber((ulong)N5_InpMagic);
   N5_g_trade.SetTypeFillingBySymbol(N5_Symbol);
   N5_g_trade.SetDeviationInPoints(N5_InpMaximumDeviationPoints);
   string prefix=(N5_InpUseMarkovRegimeFilter ? "Safe " : "");
   string comment=prefix+(direction>0 ? "N5EMA long" : "N5EMA short");
   bool sent=(direction>0 ? N5_g_trade.Buy(lots,N5_Symbol,0.0,stop,target,comment)
                          : N5_g_trade.Sell(lots,N5_Symbol,0.0,stop,target,comment));
   if(sent) N5_StoreInitialRisk();
   else Print("N5EMA order rejected: ",N5_g_trade.ResultRetcodeDescription());
   return sent;
  }

double N5_ExtremeSinceOpen(const bool buy,const datetime opened,const MqlTick &tick)
  {
   int shift=iBarShift(N5_Symbol,N5_InpSignalTimeframe,opened,false);
   if(shift<0) shift=0;
   int count=shift+1;
   double values[];
   ArraySetAsSeries(values,true);
   double extreme=(buy ? tick.bid : tick.ask);
   if(buy)
     {
      if(CopyHigh(N5_Symbol,N5_InpSignalTimeframe,0,count,values)==count)
         extreme=MathMax(extreme,values[ArrayMaximum(values)]);
     }
   else
     {
      if(CopyLow(N5_Symbol,N5_InpSignalTimeframe,0,count,values)==count)
         extreme=MathMin(extreme,values[ArrayMinimum(values)]);
     }
   return extreme;
  }

bool N5_ModifyPosition(const ulong ticket,const double stop)
  {
   double target=PositionGetDouble(POSITION_TP);
   N5_g_trade.SetExpertMagicNumber((ulong)N5_InpMagic);
   N5_g_trade.SetDeviationInPoints(N5_InpMaximumDeviationPoints);
   if(!N5_g_trade.PositionModify(ticket,N5_NormalizePrice(stop),target))
     {
      Print("N5EMA stop modification failed: ",N5_g_trade.ResultRetcodeDescription());
      return false;
     }
   return true;
  }

void N5_ManagePosition()
  {
   ulong ticket=0;
   if(!N5_SelectOurPosition(ticket)) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(N5_InpMaximumHoldingMinutes>0 && TimeCurrent()>=opened+N5_InpMaximumHoldingMinutes*60)
     {
      N5_g_trade.SetExpertMagicNumber((ulong)N5_InpMagic);
      N5_g_trade.SetDeviationInPoints(N5_InpMaximumDeviationPoints);
      if(!N5_g_trade.PositionClose(ticket,(ulong)N5_InpMaximumDeviationPoints))
         Print("N5EMA time close failed: ",N5_g_trade.ResultRetcodeDescription());
      return;
     }
   if(N5_InpCloseAtSessionEnd && N5_IsAtOrAfterSessionClose(TimeCurrent()))
     {
      N5_g_trade.SetExpertMagicNumber((ulong)N5_InpMagic);
      N5_g_trade.SetDeviationInPoints(N5_InpMaximumDeviationPoints);
      if(!N5_g_trade.PositionClose(ticket,(ulong)N5_InpMaximumDeviationPoints))
         Print("N5EMA session close failed: ",N5_g_trade.ResultRetcodeDescription());
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(N5_Symbol,tick)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double current=(buy ? tick.bid : tick.ask);
   double stop=PositionGetDouble(POSITION_SL);
   double initial_risk=N5_InitialRiskForSelectedPosition();
   if(initial_risk<=0.0) return;
   double favorable=(buy ? current-open : open-current);
   double point=SymbolInfoDouble(N5_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(N5_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(N5_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;

   if(N5_InpUseBreakEven && favorable>=N5_InpBreakEvenTriggerR*initial_risk)
     {
      double candidate=open+(buy ? 1.0 : -1.0)*N5_InpBreakEvenLockR*initial_risk;
      candidate=(buy ? MathMin(candidate,tick.bid-broker_gap) : MathMax(candidate,tick.ask+broker_gap));
      bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
      if(improves) N5_ModifyPosition(ticket,candidate);
     }

   if(N5_InpUseMATrailing && N5_g_trail_ma_handle!=INVALID_HANDLE && favorable>=N5_InpTrailMAStartR*initial_risk)
     {
      double ma=0.0;
      if(N5_ReadIndicatorValue(N5_g_trail_ma_handle,1,ma) && ma>0.0)
        {
         double candidate=(buy ? MathMin(ma,tick.bid-broker_gap) : MathMax(ma,tick.ask+broker_gap));
         candidate=N5_NormalizePrice(candidate);
         stop=PositionGetDouble(POSITION_SL);
         bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
         if(improves) N5_ModifyPosition(ticket,candidate);
        }
     }

   if(!N5_InpUseATRTrailing) return;
   if(N5_InpTrailStartR>0.0 && favorable<N5_InpTrailStartR*initial_risk) return;
   double atr=0.0;
   if(!N5_ReadIndicatorValue(N5_g_atr_handle,0,atr)) return;
   double extreme=N5_ExtremeSinceOpen(buy,opened,tick);
   double candidate=extreme+(buy ? -1.0 : 1.0)*N5_InpTrailingATR*atr;
   candidate=(buy ? MathMin(candidate,tick.bid-broker_gap) : MathMax(candidate,tick.ask+broker_gap));
   candidate=N5_NormalizePrice(candidate);
   stop=PositionGetDouble(POSITION_SL);
   bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
   if(improves) N5_ModifyPosition(ticket,candidate);
  }

bool N5_DIAgrees(const int direction)
  {
   if(!N5_InpRequireDIAgreement) return true;
   double plus_di[],minus_di[];
   // iADX buffers: 0=ADX, 1=+DI, 2=-DI. Shift 1 is the completed 09:30 NY signal bar.
   if(N5_g_adx_handle==INVALID_HANDLE || CopyBuffer(N5_g_adx_handle,1,1,1,plus_di)!=1 || CopyBuffer(N5_g_adx_handle,2,1,1,minus_di)!=1) return false;
   return (direction>0 ? plus_di[0]>minus_di[0] : minus_di[0]>plus_di[0]);
  }

bool N5_SignalQualityPasses(const int direction,const MqlRates &signal,const double ema,const double previous_ema,const double atr)
  {
   if(atr<=0.0) return false;
   double body=MathAbs(signal.close-signal.open);
   double range=signal.high-signal.low;
   double body_atr=body/atr;
   double body_fraction=(range>0.0 ? body/range : 0.0);
   double distance=MathAbs(signal.close-ema)/atr;
   if(N5_InpMinimumBodyATR>0.0 && body_atr<N5_InpMinimumBodyATR) return false;
   if(N5_InpMaximumBodyATR>0.0 && body_atr>N5_InpMaximumBodyATR) return false;
   if(N5_InpMinimumBodyFraction>0.0 && body_fraction<N5_InpMinimumBodyFraction) return false;
   if(N5_InpMinimumEMADistanceATR>0.0 && distance<N5_InpMinimumEMADistanceATR) return false;
   if(N5_InpMaximumEMADistanceATR>0.0 && distance>N5_InpMaximumEMADistanceATR) return false;
   if(N5_InpRequireEMASlope && ((direction>0 && ema<=previous_ema) || (direction<0 && ema>=previous_ema))) return false;
   if(N5_InpRelativeVolumePeriod>=2 && N5_InpMinimumRelativeVolume>0.0 && N5_RelativeVolume(1)<N5_InpMinimumRelativeVolume) return false;
   return true;
  }

void N5_ProcessNewBar()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(N5_Symbol,N5_InpSignalTimeframe,0,3,rates)!=3) return;
   if(!N5_IsNewYorkTime(rates[1].time,N5_InpSignalHourNY,N5_InpSignalMinuteNY)) return;
   int date_key=N5_NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(N5_SelectOurPosition(ticket) || N5_AlreadyTradedOnNewYorkDate(date_key) || !N5_InpEnableTrading) return;

   double ema=0.0,previous_ema=0.0,atr=0.0;
   if(!N5_ReadIndicatorValue(N5_g_ema_handle,1,ema) || !N5_ReadIndicatorValue(N5_g_ema_handle,2,previous_ema) ||
      !N5_ReadIndicatorValue(N5_g_atr_handle,1,atr)) return;
   if(!N5_CurrentSpreadPasses(atr)) return;
   int direction=(rates[1].close>ema ? 1 : (rates[1].close<ema ? -1 : 0));
   if(direction==0 || (direction>0 && !N5_InpAllowLong) || (direction<0 && !N5_InpAllowShort)) return;
   if(!N5_SignalQualityPasses(direction,rates[1],ema,previous_ema,atr)) return;
   if(!N5_DIAgrees(direction)) return;
   N5_SendEntry(direction,atr,rates[1],N5_SelectedRewardRisk(rates[1],atr));
  }

int N5_OnInit()
  {
   if(!N5_DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   bool timeframe_valid=(N5_InpSignalTimeframe==PERIOD_M1 || N5_InpSignalTimeframe==PERIOD_M5 ||
                         N5_InpSignalTimeframe==PERIOD_M15 || N5_InpSignalTimeframe==PERIOD_M30);
   if(!timeframe_valid || N5_InpSignalHourNY<0 || N5_InpSignalHourNY>23 || N5_InpSignalMinuteNY<0 || N5_InpSignalMinuteNY>59 ||
      N5_InpEMAPeriod<2 || N5_InpATRPeriod<2 || N5_InpInitialStopATR<=0.0 || N5_InpSignalStopBufferATR<0.0 ||
      N5_InpRewardRisk<=0.0 || N5_InpAdaptiveStrongRR<=0.0 || N5_InpAdaptiveStrongBodyATR<=0.0 ||
      N5_InpTrailingATR<=0.0 || N5_InpTrailStartR<0.0 || N5_InpBreakEvenTriggerR<0.0 || N5_InpBreakEvenLockR<0.0 ||
      N5_InpRiskPercent<=0.0 || N5_InpRiskPercent>10.0 || N5_InpMaximumHoldingMinutes<0 ||
      N5_InpCloseHourNY<0 || N5_InpCloseHourNY>23 || N5_InpCloseMinuteNY<0 || N5_InpCloseMinuteNY>59 ||
      N5_InpMinimumBodyATR<0.0 || N5_InpMaximumBodyATR<0.0 || N5_InpMinimumBodyFraction<0.0 || N5_InpMinimumBodyFraction>1.0 ||
      N5_InpMinimumEMADistanceATR<0.0 || N5_InpMaximumEMADistanceATR<0.0 || N5_InpRelativeVolumePeriod<0 || N5_InpMinimumRelativeVolume<0.0 || N5_InpDIPeriod<2)
      return INIT_PARAMETERS_INCORRECT;
   N5_g_ema_handle=iMA(N5_Symbol,N5_InpSignalTimeframe,N5_InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   N5_g_atr_handle=iATR(N5_Symbol,N5_InpSignalTimeframe,N5_InpATRPeriod);
   if(N5_g_ema_handle==INVALID_HANDLE || N5_g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(N5_InpRequireDIAgreement)
     {
      N5_g_adx_handle=iADX(N5_Symbol,N5_InpSignalTimeframe,N5_InpDIPeriod);
      if(N5_g_adx_handle==INVALID_HANDLE) return INIT_FAILED;
     }
   if(N5_InpUseMATrailing)
     {
      if(N5_InpTrailMAPeriod<2 || N5_InpTrailMAStartR<0.0) return INIT_PARAMETERS_INCORRECT;
      N5_g_trail_ma_handle=iMA(N5_Symbol,N5_InpSignalTimeframe,N5_InpTrailMAPeriod,0,N5_InpTrailMAMethod,PRICE_CLOSE);
      if(N5_g_trail_ma_handle==INVALID_HANDLE) return INIT_FAILED;
     }
   if(N5_InpStopMode==N5_N5_STOP_PERCENT && (N5_InpInitialStopPercent<=0.0 || N5_InpInitialStopPercent>10.0)) return INIT_PARAMETERS_INCORRECT;
   N5_g_trade.SetExpertMagicNumber((ulong)N5_InpMagic);
   N5_g_trade.SetTypeFillingBySymbol(N5_Symbol);
   N5_g_last_bar_time=iTime(N5_Symbol,N5_InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
  }

void N5_OnDeinit(const int reason)
  {
   if(N5_g_ema_handle!=INVALID_HANDLE) IndicatorRelease(N5_g_ema_handle);
   if(N5_g_atr_handle!=INVALID_HANDLE) IndicatorRelease(N5_g_atr_handle);
   if(N5_g_adx_handle!=INVALID_HANDLE) IndicatorRelease(N5_g_adx_handle);
   if(N5_g_trail_ma_handle!=INVALID_HANDLE) IndicatorRelease(N5_g_trail_ma_handle);
  }

void N5_OnTick()
  {
   N5_DTS_ManageDynamicTrailing(N5_InpMagic);
   N5_ManagePosition();
   datetime bar_time=iTime(N5_Symbol,N5_InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==N5_g_last_bar_time) return;
   N5_g_last_bar_time=bar_time;
   N5_ProcessNewBar();
  }


const string RV_Symbol="XAUUSD";
const ENUM_TIMEFRAMES RV_Period=(ENUM_TIMEFRAMES)16385;




enum RV_ENUM_RV_EXIT_MODE
  {
   RV_RV_EXIT_SIGNAL=0,
   RV_RV_EXIT_FIXED_RR=1,
   RV_RV_EXIT_RR_TRAIL=2
  };

enum RV_ENUM_RV_STOP_MODE
  {
   RV_RV_STOP_ATR=0,
   RV_RV_STOP_SWING=1,
   RV_RV_STOP_VWAP=2
  };

enum RV_ENUM_RV_SESSION
  {
   RV_RV_SESSION_ALL=0,
   RV_RV_SESSION_ASIA=1,
   RV_RV_SESSION_LONDON=2,
   RV_RV_SESSION_NEW_YORK=3,
   RV_RV_SESSION_OVERLAP=4
  };

const int RV_InpRSILength=16;
const double RV_InpOversold=18.0;
const double RV_InpOverbought=80.0;
const double RV_InpRiskPercent=1.0;
const bool RV_InpAdaptivePortfolioControls=false;
const RV_ENUM_RV_EXIT_MODE RV_InpExitMode=(RV_ENUM_RV_EXIT_MODE)2;
const RV_ENUM_RV_STOP_MODE RV_InpStopMode=(RV_ENUM_RV_STOP_MODE)1;
const int RV_InpATRPeriod=14;
const double RV_InpStopATR=2;
const int RV_InpSwingLookback=5;
const double RV_InpStopBufferATR=0.10;
const double RV_InpRewardRisk=0.5;
const double RV_InpSignalClosePercent=100.0;
const bool RV_InpUseBreakEven=true;
const double RV_InpBreakEvenAtR=0.75;
const double RV_InpBreakEvenLockR=0.05;
const bool RV_InpUseATRTrailing=false;
const double RV_InpTrailStartR=1;
const double RV_InpTrailATR=2;
const int RV_InpMaximumHoldingBars=0;
const RV_ENUM_RV_SESSION RV_InpSession=(RV_ENUM_RV_SESSION)0;
const int RV_InpMaximumSpreadPoints=0;
const int RV_InpMaximumDeviationPoints=80;
const long RV_InpMagic=926400006;

CTrade RV_trade;
int RV_atr_handle=INVALID_HANDLE;
datetime RV_last_bar_time=0;

int RV_VolumeDigits(const double step)
  {
   if(step>=1.0) return 0;
   if(step>=0.1) return 1;
   if(step>=0.01) return 2;
   if(step>=0.001) return 3;
   return 4;
  }

double RV_NormalizeVolume(const double requested,const bool round_up=true)
  {
   const double minimum=SymbolInfoDouble(RV_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(RV_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(RV_Symbol,SYMBOL_VOLUME_STEP);
   if(requested<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0) return 0.0;
   if(!round_up && requested<minimum) return 0.0;
   double volume=round_up
      ? MathCeil((MathMin(requested,maximum)-1e-12)/step)*step
      : MathFloor((MathMin(requested,maximum)+1e-12)/step)*step;
   volume=MathMin(maximum,volume);
   if(round_up) volume=MathMax(minimum,volume);
   else if(volume<minimum) return 0.0;
   if(round_up && volume>requested+1e-12)
      PrintFormat("RSI VWAP risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",requested,volume);
   return NormalizeDouble(volume,RV_VolumeDigits(step));
  }

bool RV_OwnPosition(ulong &ticket)
  {
   ticket=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      const ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=RV_Symbol) continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=RV_InpMagic) continue;
      ticket=candidate;
      return true;
     }
   return false;
  }

bool RV_ReadATR(const int shift,double &value)
  {
   double buffer[1];
   if(RV_atr_handle==INVALID_HANDLE || CopyBuffer(RV_atr_handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0 && MathIsValidNumber(value);
  }

bool RV_BuildRsiVwap(double &rsi_closed_1,double &rsi_closed_2,double &vwap_closed_1)
  {
   const int wanted=MathMax(600,RV_InpRSILength*30);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(RV_Symbol,RV_Period,0,wanted,rates);
   if(copied<RV_InpRSILength+20) return false;

   double chronological_vwap[];
   double chronological_rsi[];
   ArrayResize(chronological_vwap,copied);
   ArrayResize(chronological_rsi,copied);
   ArrayInitialize(chronological_rsi,EMPTY_VALUE);

   double sum_price_volume=0.0;
   double sum_volume=0.0;
   int day_key=-1;
   for(int chrono=0;chrono<copied;chrono++)
     {
      const int series_index=copied-1-chrono;
      MqlDateTime stamp;
      TimeToStruct(rates[series_index].time,stamp);
      const int key=stamp.year*1000+stamp.day_of_year;
      if(key!=day_key)
        {
         day_key=key;
         sum_price_volume=0.0;
         sum_volume=0.0;
        }
      double volume=(double)rates[series_index].real_volume;
      if(volume<=0.0) volume=(double)rates[series_index].tick_volume;
      if(volume<=0.0) volume=1.0;
      sum_price_volume+=rates[series_index].close*volume;
      sum_volume+=volume;
      chronological_vwap[chrono]=sum_price_volume/sum_volume;
     }

   double average_gain=0.0;
   double average_loss=0.0;
   for(int chrono=1;chrono<copied;chrono++)
     {
      const double change=chronological_vwap[chrono]-chronological_vwap[chrono-1];
      const double gain=MathMax(change,0.0);
      const double loss=MathMax(-change,0.0);
      if(chrono<=RV_InpRSILength)
        {
         average_gain+=gain;
         average_loss+=loss;
         if(chrono==RV_InpRSILength)
           {
            average_gain/=RV_InpRSILength;
            average_loss/=RV_InpRSILength;
           }
        }
      else
        {
         average_gain=(average_gain*(RV_InpRSILength-1)+gain)/RV_InpRSILength;
         average_loss=(average_loss*(RV_InpRSILength-1)+loss)/RV_InpRSILength;
        }
      if(chrono>=RV_InpRSILength)
        {
         if(average_loss<=0.0) chronological_rsi[chrono]=100.0;
         else
           {
            const double relative_strength=average_gain/average_loss;
            chronological_rsi[chrono]=100.0-100.0/(1.0+relative_strength);
           }
        }
     }

   const int chrono_1=copied-2;
   const int chrono_2=copied-3;
   if(chrono_2<RV_InpRSILength || chronological_rsi[chrono_1]==EMPTY_VALUE || chronological_rsi[chrono_2]==EMPTY_VALUE)
      return false;
   rsi_closed_1=chronological_rsi[chrono_1];
   rsi_closed_2=chronological_rsi[chrono_2];
   vwap_closed_1=chronological_vwap[chrono_1];
   return MathIsValidNumber(rsi_closed_1) && MathIsValidNumber(rsi_closed_2);
  }

bool RV_SessionAllowed(const datetime signal_time)
  {
   if(RV_InpSession==RV_RV_SESSION_ALL) return true;
   MqlDateTime stamp;
   TimeToStruct(signal_time,stamp);
   const int hour=stamp.hour;
   if(RV_InpSession==RV_RV_SESSION_ASIA) return hour>=0 && hour<8;
   if(RV_InpSession==RV_RV_SESSION_LONDON) return hour>=7 && hour<13;
   if(RV_InpSession==RV_RV_SESSION_NEW_YORK) return hour>=12 && hour<21;
   if(RV_InpSession==RV_RV_SESSION_OVERLAP) return hour>=12 && hour<16;
   return true;
  }

bool RV_SpreadAllowed()
  {
   if(RV_InpMaximumSpreadPoints<=0) return true;
   const double ask=SymbolInfoDouble(RV_Symbol,SYMBOL_ASK);
   const double bid=SymbolInfoDouble(RV_Symbol,SYMBOL_BID);
   const double point=SymbolInfoDouble(RV_Symbol,SYMBOL_POINT);
   if(point<=0.0) return false;
   return (ask-bid)/point<=RV_InpMaximumSpreadPoints;
  }

double RV_BuildStop(const double entry,const double atr,const double vwap)
  {
   double stop=entry-RV_InpStopATR*atr;
   if(RV_InpStopMode==RV_RV_STOP_SWING)
     {
      const int count=MathMax(2,RV_InpSwingLookback);
      double lows[];
      ArraySetAsSeries(lows,true);
      if(CopyLow(RV_Symbol,RV_Period,1,count,lows)==count)
        {
         int minimum_index=ArrayMinimum(lows,0,count);
         if(minimum_index>=0) stop=lows[minimum_index]-RV_InpStopBufferATR*atr;
        }
     }
   else if(RV_InpStopMode==RV_RV_STOP_VWAP)
     {
      stop=vwap-RV_InpStopBufferATR*atr;
      if(stop>=entry || entry-stop<0.25*atr) stop=entry-RV_InpStopATR*atr;
     }
   const int stop_level=(int)SymbolInfoInteger(RV_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const double point=SymbolInfoDouble(RV_Symbol,SYMBOL_POINT);
   const double minimum_distance=(stop_level+2)*point;
   if(entry-stop<minimum_distance) stop=entry-minimum_distance;
   return NormalizeDouble(stop,(int)SymbolInfoInteger(RV_Symbol,SYMBOL_DIGITS));
  }

double RV_RiskVolume(const double entry,const double stop)
  {
   if(entry<=stop || RV_InpRiskPercent<=0.0) return 0.0;
   double loss=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,RV_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(RV_InpAdaptivePortfolioControls,RV_InpMagic);
   if(adaptive<=0.0) return 0.0;
   const double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*RV_InpRiskPercent*adaptive/100.0;
   return RV_NormalizeVolume(risk_money/loss);
  }

void RV_CloseBySignal(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)) return;
   const double current=PositionGetDouble(POSITION_VOLUME);
   const double minimum=SymbolInfoDouble(RV_Symbol,SYMBOL_VOLUME_MIN);
   if(RV_InpSignalClosePercent>=99.999 || current<=minimum)
     {
      RV_trade.PositionClose(ticket,RV_InpMaximumDeviationPoints);
      return;
     }
   const double requested=RV_NormalizeVolume(current*RV_InpSignalClosePercent/100.0,false);
   if(requested>=current-minimum/2.0) RV_trade.PositionClose(ticket,RV_InpMaximumDeviationPoints);
   else if(requested>=minimum) RV_trade.PositionClosePartial(ticket,requested,RV_InpMaximumDeviationPoints);
  }

void RV_ManagePosition()
  {
   ulong ticket=0;
   if(!RV_OwnPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   const double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   const double current_stop=PositionGetDouble(POSITION_SL);
   const double current_tp=PositionGetDouble(POSITION_TP);
   const double bid=SymbolInfoDouble(RV_Symbol,SYMBOL_BID);
   if(entry<=0.0 || current_stop<=0.0 || bid<=entry) return;
   // A trailed stop must not redefine one R.  Fixed-RR positions preserve the
   // original risk in their take-profit distance; fall back to the live stop
   // only for signal-only exits that have no TP.
   double initial_risk=entry-current_stop;
   if(current_tp>entry && RV_InpRewardRisk>0.0)
      initial_risk=(current_tp-entry)/RV_InpRewardRisk;
   if(initial_risk<=0.0) return;
   double candidate=current_stop;
   if(RV_InpUseBreakEven && bid-entry>=RV_InpBreakEvenAtR*initial_risk)
      candidate=MathMax(candidate,entry+RV_InpBreakEvenLockR*initial_risk);
   if(RV_InpUseATRTrailing && bid-entry>=RV_InpTrailStartR*initial_risk)
     {
      double atr=0.0;
      if(RV_ReadATR(0,atr)) candidate=MathMax(candidate,bid-RV_InpTrailATR*atr);
     }
   const double point=SymbolInfoDouble(RV_Symbol,SYMBOL_POINT);
   const int stops=(int)SymbolInfoInteger(RV_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   candidate=MathMin(candidate,bid-(stops+2)*point);
   candidate=NormalizeDouble(candidate,(int)SymbolInfoInteger(RV_Symbol,SYMBOL_DIGITS));
   if(candidate>current_stop+point) RV_trade.PositionModify(ticket,candidate,current_tp);
  }

void RV_CheckMaximumHold(const ulong ticket)
  {
   if(RV_InpMaximumHoldingBars<=0 || !PositionSelectByTicket(ticket)) return;
   const datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   const int seconds=PeriodSeconds(RV_Period);
   if(seconds>0 && TimeCurrent()-opened>=(long)RV_InpMaximumHoldingBars*seconds)
      RV_trade.PositionClose(ticket,RV_InpMaximumDeviationPoints);
  }

void RV_ProcessNewBar()
  {
   double rsi_1=0.0,rsi_2=0.0,vwap_1=0.0;
   if(!RV_BuildRsiVwap(rsi_1,rsi_2,vwap_1)) return;
   ulong ticket=0;
   const bool has_position=RV_OwnPosition(ticket);
   const bool exit_signal=(rsi_2>=RV_InpOverbought && rsi_1<RV_InpOverbought);
   if(has_position)
     {
      RV_CheckMaximumHold(ticket);
      if(exit_signal && RV_OwnPosition(ticket)) RV_CloseBySignal(ticket);
      return;
     }

   const bool entry_signal=(rsi_2<=RV_InpOversold && rsi_1>RV_InpOversold);
   if(!entry_signal || !RV_SpreadAllowed()) return;
   const datetime signal_time=iTime(RV_Symbol,RV_Period,1);
   if(!RV_SessionAllowed(signal_time)) return;
   double atr=0.0;
   if(!RV_ReadATR(1,atr)) return;
   const double entry=SymbolInfoDouble(RV_Symbol,SYMBOL_ASK);
   const double stop=RV_BuildStop(entry,atr,vwap_1);
   const double volume=RV_RiskVolume(entry,stop);
   if(volume<=0.0) return;
   double take_profit=0.0;
   if(RV_InpExitMode!=RV_RV_EXIT_SIGNAL)
      take_profit=NormalizeDouble(entry+RV_InpRewardRisk*(entry-stop),(int)SymbolInfoInteger(RV_Symbol,SYMBOL_DIGITS));
   RV_trade.SetExpertMagicNumber(RV_InpMagic);
   RV_trade.SetDeviationInPoints(RV_InpMaximumDeviationPoints);
   RV_trade.SetTypeFillingBySymbol(RV_Symbol);
   RV_trade.Buy(volume,RV_Symbol,0.0,stop,take_profit,"RSI-VWAP long");
  }

int RV_OnInit()
  {
   if(RV_InpRSILength<2 || RV_InpOversold<0.0 || RV_InpOverbought>100.0 || RV_InpOversold>=RV_InpOverbought)
      return INIT_PARAMETERS_INCORRECT;
   RV_atr_handle=iATR(RV_Symbol,RV_Period,RV_InpATRPeriod);
   if(RV_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   RV_trade.SetExpertMagicNumber(RV_InpMagic);
   RV_trade.SetDeviationInPoints(RV_InpMaximumDeviationPoints);
   RV_last_bar_time=iTime(RV_Symbol,RV_Period,0);
   return INIT_SUCCEEDED;
  }

void RV_OnDeinit(const int reason)
  {
   if(RV_atr_handle!=INVALID_HANDLE) IndicatorRelease(RV_atr_handle);
  }

void RV_OnTick()
  {
   RV_ManagePosition();
   const datetime current=iTime(RV_Symbol,RV_Period,0);
   if(current<=0 || current==RV_last_bar_time) return;
   RV_last_bar_time=current;
   RV_ProcessNewBar();
  }


const string E3_Symbol="XAUUSD";
const ENUM_TIMEFRAMES E3_Period=(ENUM_TIMEFRAMES)16388;



#define E3_AAA_STRATEGY_ID 1
#define E3_AAA_STRATEGY_NAME "AAA Final EMA3"
#define E3_AAA_DEFAULT_ENABLED true
#define E3_AAA_DEFAULT_RISK 1.0
#define E3_AAA_DEFAULT_RR 1.7
#define E3_AAA_DEFAULT_MAGIC 3082026
const bool E3_InpAdaptivePortfolioControls=false;

#define E3_AAA_FINAL_STRATEGY_ENGINE_MQH

#define E3_AAA_FINAL_COMMON_MQH

#define E3_DYNAMIC_TRAILING_SESSION_FILTER_MQH

enum E3_ENUM_DTS_SESSION_MODE
  {
   E3_DTS_SESSION_ALL=0,
   E3_DTS_SESSION_ASIA=1,
   E3_DTS_SESSION_LONDON=2,
   E3_DTS_SESSION_NEW_YORK=3,
   E3_DTS_SESSION_LONDON_NEW_YORK_OVERLAP=4
  };
const bool E3_InpUseDynamicTrailingSL=true;
const double E3_InpDynamicTriggerFraction=0.60;
const double E3_InpDynamicLockFraction=0.20;
const E3_ENUM_DTS_SESSION_MODE E3_InpResearchSession=(E3_ENUM_DTS_SESSION_MODE)0;
const int E3_InpResearchBrokerUtcOffsetMinutes=0;

struct E3_DTS_TRACKED_POSITION
  {
   ulong    identifier;
   datetime opened;
   double   target_distance;
  };

E3_DTS_TRACKED_POSITION E3_g_dts_positions[];
datetime E3_g_dts_last_m15_bar=0;

bool E3_DTS_InputsValid()
  {
   return E3_InpDynamicTriggerFraction>0.0 && E3_InpDynamicTriggerFraction<=1.0 &&
          E3_InpDynamicLockFraction>=0.0 && E3_InpDynamicLockFraction<E3_InpDynamicTriggerFraction &&
          E3_InpResearchBrokerUtcOffsetMinutes>=-840 && E3_InpResearchBrokerUtcOffsetMinutes<=840;
  }

bool E3_DTS_MinuteInside(const int minute_of_day,const int start_minute,const int end_minute)
  {
   if(start_minute==end_minute) return true;
   if(start_minute<end_minute) return minute_of_day>=start_minute && minute_of_day<end_minute;
   return minute_of_day>=start_minute || minute_of_day<end_minute;
  }

bool E3_DTS_EntrySessionAllowed()
  {
   if(E3_InpResearchSession==E3_DTS_SESSION_ALL) return true;
   datetime utc=TimeCurrent()-E3_InpResearchBrokerUtcOffsetMinutes*60;
   MqlDateTime now; TimeToStruct(utc,now);
   int minute_of_day=now.hour*60+now.min;
   if(E3_InpResearchSession==E3_DTS_SESSION_ASIA)
      return E3_DTS_MinuteInside(minute_of_day,0,8*60);
   if(E3_InpResearchSession==E3_DTS_SESSION_LONDON)
      return E3_DTS_MinuteInside(minute_of_day,7*60,12*60);
   if(E3_InpResearchSession==E3_DTS_SESSION_NEW_YORK)
      return E3_DTS_MinuteInside(minute_of_day,13*60,21*60);
   if(E3_InpResearchSession==E3_DTS_SESSION_LONDON_NEW_YORK_OVERLAP)
      return E3_DTS_MinuteInside(minute_of_day,13*60,16*60);
   return true;
  }

int E3_DTS_FindTracked(const ulong identifier)
  {
   for(int i=0;i<ArraySize(E3_g_dts_positions);i++)
      if(E3_g_dts_positions[i].identifier==identifier) return i;
   return -1;
  }

void E3_DTS_ObservePositions(const long magic)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=E3_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(E3_DTS_FindTracked(identifier)>=0) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double target=PositionGetDouble(POSITION_TP);
      double stop=PositionGetDouble(POSITION_SL);
      double distance=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(target>entry) distance=target-entry;
         else if(stop>0.0 && stop<entry) distance=entry-stop;
        }
      else
        {
         if(target>0.0 && target<entry) distance=entry-target;
         else if(stop>entry) distance=stop-entry;
        }
      if(distance<=SymbolInfoDouble(E3_Symbol,SYMBOL_POINT)) continue;
      int size=ArraySize(E3_g_dts_positions);
      ArrayResize(E3_g_dts_positions,size+1);
      E3_g_dts_positions[size].identifier=identifier;
      E3_g_dts_positions[size].opened=(datetime)PositionGetInteger(POSITION_TIME);
      E3_g_dts_positions[size].target_distance=distance;
     }
  }

bool E3_DTS_ModifyStop(const ulong ticket,const double stop,const double target)
  {
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.symbol=E3_Symbol;
   request.sl=NormalizeDouble(stop,(int)SymbolInfoInteger(E3_Symbol,SYMBOL_DIGITS));
   request.tp=target;
   if(!OrderSend(request,result)) return false;
   return result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED || result.retcode==TRADE_RETCODE_NO_CHANGES;
  }

void E3_DTS_ManageDynamicTrailing(const long magic)
  {
   if(!E3_InpUseDynamicTrailingSL) return;
   E3_DTS_ObservePositions(magic);
   datetime current_m15=iTime(E3_Symbol,PERIOD_M15,0);
   if(current_m15<=0) return;
   if(E3_g_dts_last_m15_bar==0)
     {
      E3_g_dts_last_m15_bar=current_m15;
      return;
     }
   if(current_m15==E3_g_dts_last_m15_bar) return;
   E3_g_dts_last_m15_bar=current_m15;
   double closed_price=iClose(E3_Symbol,PERIOD_M15,1);
   if(closed_price<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(E3_Symbol,tick)) return;
   double point=SymbolInfoDouble(E3_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax(point,SymbolInfoInteger(E3_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=E3_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      int tracked=E3_DTS_FindTracked(identifier);
      if(tracked<0 || E3_g_dts_positions[tracked].target_distance<=point) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double distance=E3_g_dts_positions[tracked].target_distance;
      double desired=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(closed_price<entry+E3_InpDynamicTriggerFraction*distance) continue;
         desired=entry+E3_InpDynamicLockFraction*distance;
         desired=MathMin(desired,tick.bid-broker_gap);
         if(desired<=entry || (current_stop>0.0 && desired<=current_stop+point)) continue;
        }
      else
        {
         if(closed_price>entry-E3_InpDynamicTriggerFraction*distance) continue;
         desired=entry-E3_InpDynamicLockFraction*distance;
         desired=MathMax(desired,tick.ask+broker_gap);
         if(desired>=entry || (current_stop>0.0 && desired>=current_stop-point)) continue;
        }
      if(!E3_DTS_ModifyStop(ticket,desired,target))
         Print("Dynamic trailing SL modification failed for position ",ticket);
     }
  }


CTrade E3_AAA_Trade;
int E3_AAA_TesterServerOffsetMode=1; // 1 = EET/EEST broker clock, used only in the Strategy Tester

double E3_AAA_Price(const string symbol,const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
}

double E3_AAA_Volume(const string symbol,const double raw)
{
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   if(lots>raw+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw,lots);
   return NormalizeDouble(lots,8);
}

double E3_AAA_LotsForRisk(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double risk_percent)
{
   if(risk_percent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double loss=MathAbs(one_lot_result);
   if(loss<=0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(E3_InpAdaptivePortfolioControls,E3_InpMagic);
   if(adaptive<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*risk_percent*adaptive/100.0;
   return E3_AAA_Volume(symbol,risk_cash/loss);
}

bool E3_AAA_HasPosition(const string symbol,const long magic)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==symbol && PositionGetInteger(POSITION_MAGIC)==magic) return true;
   }
   return false;
}

bool E3_AAA_HasOrder(const string symbol,const long magic)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic) return true;
   }
   return false;
}

bool E3_AAA_HasExposure(const string symbol,const long magic)
{
   return E3_AAA_HasPosition(symbol,magic) || E3_AAA_HasOrder(symbol,magic);
}

void E3_AAA_DeleteOrders(const string symbol,const long magic)
{
   E3_AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic)
         E3_AAA_Trade.OrderDelete(ticket);
   }
}

bool E3_AAA_NewBar(const string symbol,const ENUM_TIMEFRAMES timeframe,datetime &last_bar)
{
   datetime current=iTime(symbol,timeframe,0);
   if(current<=0 || current==last_bar) return false;
   last_bar=current;
   return true;
}

double E3_AAA_BufferValue(const int handle,const int buffer,const int shift)
{
   if(handle==INVALID_HANDLE) return EMPTY_VALUE;
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,buffer,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

double E3_AAA_ATR(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iATR(symbol,timeframe,period);
   double value=E3_AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double E3_AAA_MA(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift,const ENUM_MA_METHOD method=MODE_EMA)
{
   int handle=iMA(symbol,timeframe,period,0,method,PRICE_CLOSE);
   double value=E3_AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double E3_AAA_RSI(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iRSI(symbol,timeframe,period,PRICE_CLOSE);
   double value=E3_AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double E3_AAA_ADX(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iADX(symbol,timeframe,period);
   double value=E3_AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

int E3_AAA_DaysInMonth(const int year,const int month)
{
   if(month==2) return ((year%4==0 && year%100!=0) || year%400==0 ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int E3_AAA_LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=E3_AAA_DaysInMonth(year,month); p.hour=12;
   datetime stamp=StructToTime(p);
   TimeToStruct(stamp,p);
   return E3_AAA_DaysInMonth(year,month)-p.day_of_week;
}

int E3_AAA_TesterEETOffsetSeconds(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(server_time,p);
   bool summer=false;
   if(p.mon>3 && p.mon<10) summer=true;
   else if(p.mon==3)
   {
      int last=E3_AAA_LastSunday(p.year,3);
      summer=(p.day>last || (p.day==last && p.hour>=3));
   }
   else if(p.mon==10)
   {
      int last=E3_AAA_LastSunday(p.year,10);
      summer=(p.day<last || (p.day==last && p.hour<4));
   }
   return (summer ? 3 : 2)*3600;
}

int E3_AAA_ServerOffsetSeconds()
{
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   // In MT5 tests TimeGMT() is simulated as server time. Rebuild the active
   // broker's EET/EEST offset so UTC and New York session rules remain testable.
   if((bool)MQLInfoInteger(MQL_TESTER) && E3_AAA_TesterServerOffsetMode==1)
      return E3_AAA_TesterEETOffsetSeconds(server);
   return (int)(server-TimeGMT());
}

datetime E3_AAA_ToUTC(const datetime server_time)
{
   return server_time-E3_AAA_ServerOffsetSeconds();
}

datetime E3_AAA_ToServer(const datetime utc_time)
{
   return utc_time+E3_AAA_ServerOffsetSeconds();
}

int E3_AAA_UTCDateKey(const datetime server_time)
{
   MqlDateTime part;
   TimeToStruct(E3_AAA_ToUTC(server_time),part);
   return part.year*10000+part.mon*100+part.day;
}

datetime E3_AAA_UTCDateTime(const datetime server_time,const int hour,const int minute=0)
{
   MqlDateTime part;
   TimeToStruct(E3_AAA_ToUTC(server_time),part);
   part.hour=hour;
   part.min=minute;
   part.sec=0;
   return E3_AAA_ToServer(StructToTime(part));
}

int E3_AAA_NewYorkOffsetHours(const datetime utc_time)
{
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   // Sufficient deterministic DST approximation for trading-window selection.
   if(p.mon>3 && p.mon<11) return -4;
   if(p.mon<3 || p.mon>11) return -5;
   if(p.mon==3 && p.day>=8) return -4;
   if(p.mon==11 && p.day<8) return -4;
   return -5;
}

datetime E3_AAA_ToNewYork(const datetime server_time)
{
   datetime utc=E3_AAA_ToUTC(server_time);
   return utc+E3_AAA_NewYorkOffsetHours(utc)*3600;
}

datetime E3_AAA_NewYorkToServer(const datetime ny_time)
{
   MqlDateTime p;
   TimeToStruct(ny_time,p);
   // Resolve using the same calendar day; the DST approximation above is stable around session hours.
   datetime guessed_utc=ny_time+5*3600;
   int offset=E3_AAA_NewYorkOffsetHours(guessed_utc);
   return E3_AAA_ToServer(ny_time-offset*3600);
}

bool E3_AAA_SessionRangeUTC(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now=TimeCurrent();
   datetime from=E3_AAA_UTCDateTime(now,start_hour);
   datetime to=E3_AAA_UTCDateTime(now,end_hour)-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX;
   low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool E3_AAA_SessionRangeNY(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now_ny=E3_AAA_ToNewYork(TimeCurrent());
   MqlDateTime p;
   TimeToStruct(now_ny,p);
   p.hour=start_hour; p.min=0; p.sec=0;
   datetime from=E3_AAA_NewYorkToServer(StructToTime(p));
   p.hour=end_hour;
   datetime to=E3_AAA_NewYorkToServer(StructToTime(p))-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX; low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool E3_AAA_TradedToday(const string symbol,const long magic)
{
   datetime start=E3_AAA_UTCDateTime(TimeCurrent(),0);
   if(!HistorySelect(start,TimeCurrent())) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)==symbol && HistoryDealGetInteger(ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN) return true;
   }
   return false;
}

bool E3_AAA_SendMarket(const string symbol,const int direction,const double stop,const double reward_risk,const double risk_percent,const long magic,const string comment)
{
   if(!E3_DTS_EntrySessionAllowed()) return false;
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=E3_AAA_Price(symbol,stop);
   if((direction>0 && sl>=entry) || (direction<0 && sl<=entry)) return false;
   double tp=E3_AAA_Price(symbol,entry+direction*MathAbs(entry-sl)*reward_risk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=E3_AAA_LotsForRisk(symbol,type,entry,sl,risk_percent);
   if(lots<=0.0)
   {
      Print(comment,": size below broker minimum or contract data unavailable");
      return false;
   }
   E3_AAA_Trade.SetExpertMagicNumber((ulong)magic);
   E3_AAA_Trade.SetTypeFillingBySymbol(symbol);
   E3_AAA_Trade.SetDeviationInPoints(20);
   if(direction>0) return E3_AAA_Trade.Buy(lots,symbol,0.0,sl,tp,comment);
   return E3_AAA_Trade.Sell(lots,symbol,0.0,sl,tp,comment);
}

bool E3_AAA_SendPending(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double reward_risk,const double risk_percent,const long magic,const datetime expiry,const string comment)
{
   if(!E3_DTS_EntrySessionAllowed()) return false;
   int direction=(type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_BUY_LIMIT ? 1 : -1);
   double price=E3_AAA_Price(symbol,entry);
   double sl=E3_AAA_Price(symbol,stop);
   if((direction>0 && sl>=price) || (direction<0 && sl<=price)) return false;
   double tp=E3_AAA_Price(symbol,price+direction*MathAbs(price-sl)*reward_risk);
   double lots=E3_AAA_LotsForRisk(symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),price,sl,risk_percent);
   if(lots<=0.0) return false;
   E3_AAA_Trade.SetExpertMagicNumber((ulong)magic);
   E3_AAA_Trade.SetTypeFillingBySymbol(symbol);
   if(type==ORDER_TYPE_BUY_STOP) return E3_AAA_Trade.BuyStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_STOP) return E3_AAA_Trade.SellStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_BUY_LIMIT) return E3_AAA_Trade.BuyLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_LIMIT) return E3_AAA_Trade.SellLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   return false;
}

void E3_AAA_ManageOCO(const string symbol,const long magic)
{
   if(E3_AAA_HasPosition(symbol,magic)) E3_AAA_DeleteOrders(symbol,magic);
}

void E3_AAA_TrailR(const string symbol,const long magic,const double start_r,const double distance_r)
{
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return;
   E3_AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double sl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      if(sl<=0.0 || tp<=0.0) continue;
      int direction=(type==POSITION_TYPE_BUY ? 1 : -1);
      double initial_r=MathAbs(tp-open);
      double rr=1.0;
      if(initial_r>0.0) rr=MathMax(0.1,initial_r/MathMax(MathAbs(open-sl),SymbolInfoDouble(symbol,SYMBOL_POINT)));
      initial_r=initial_r/rr;
      double price=(direction>0 ? tick.bid : tick.ask);
      if(direction*(price-open)<start_r*initial_r) continue;
      double candidate=E3_AAA_Price(symbol,price-direction*distance_r*initial_r);
      if((direction>0 && candidate>sl && candidate<price) || (direction<0 && (sl==0.0 || candidate<sl) && candidate>price))
         E3_AAA_Trade.PositionModify(ticket,candidate,tp);
   }
}



#define E3_HAMA_PER_EA_SAFE_REGIME_FILTER_MQH

// This gate is compiled into each EA that includes this file. It has no
// account-wide state and cannot approve or reject another EA's trades.
const bool E3_InpUseMarkovRegimeFilter=false;
const int E3_InpMarkovReturnWindow=40;
const double E3_InpMarkovThreshold=0.05;
const double E3_InpMarkovSignalGate=0.05;
const int E3_InpMarkovMinLabels=252;
const int E3_InpMarkovHistoryBars=2600;

int E3_HAMA_SafeRegimeStateAt(double &closes[],const int index)
{
   double older=closes[index+E3_InpMarkovReturnWindow];
   if(older<=0.0) return 1;
   double rolling_return=closes[index]/older-1.0;
   if(rolling_return>E3_InpMarkovThreshold) return 2;
   if(rolling_return<-E3_InpMarkovThreshold) return 0;
   return 1;
}

bool E3_HAMA_SafeRegimeAllowsDirection(const int direction)
{
   if(!E3_InpUseMarkovRegimeFilter) return true;
   int available=Bars(E3_Symbol,PERIOD_D1)-1;
   int requested=MathMin(E3_InpMarkovHistoryBars,available);
   if(requested<=E3_InpMarkovReturnWindow+E3_InpMarkovMinLabels) return false;

   double closes[];
   ArraySetAsSeries(closes,true);
   int copied=CopyClose(E3_Symbol,PERIOD_D1,1,requested,closes);
   int labels=copied-E3_InpMarkovReturnWindow;
   if(labels<=E3_InpMarkovMinLabels) return false;

   double counts[3][3];
   for(int row=0;row<3;row++)
      for(int col=0;col<3;col++) counts[row][col]=0.0;

   // The newest completed D1 label is used only as the forecast state. The
   // transition into it is excluded, matching the no-lookahead research.
   int oldest=labels-1;
   for(int newer=oldest-1;newer>=1;newer--)
   {
      int from=E3_HAMA_SafeRegimeStateAt(closes,newer+1);
      int to=E3_HAMA_SafeRegimeStateAt(closes,newer);
      counts[from][to]+=1.0;
   }

   int state=E3_HAMA_SafeRegimeStateAt(closes,0);
   double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0) return false;
   double signal=(counts[state][2]-counts[state][0])/total;
   return (direction>0 ? signal>E3_InpMarkovSignalGate : signal<-E3_InpMarkovSignalGate);
}


#define E3_AAA_ID_EMA3             1
#define E3_AAA_ID_ASIA             2
#define E3_AAA_ID_DMC              3
#define E3_AAA_ID_AMD              4
#define E3_AAA_ID_US100_WEAKNESS    5
#define E3_AAA_ID_NEWS_PULSE       6
#define E3_AAA_ID_WEEKEND          7
#define E3_AAA_ID_XAU_GRID         8
#define E3_AAA_ID_XAU_WEAKNESS     9
#define E3_AAA_ID_XAU_US100_PORT  10

const bool E3_InpEnableTrading=true;
const double E3_InpRiskPercent=1.0;
const double E3_InpRewardRisk=1.7;
const long E3_InpMagic=3082026;
const int E3_InpMaxSpreadPoints=0;
const int E3_InpTesterServerClockMode=1; // 1 = EET/EEST (MEX Atlantic); live trading ignores this
const int E3_InpPivotBars=5;
const int E3_InpTrendEMA=200;
const int E3_InpTrendSlopeBars=6;
const bool E3_InpUseTrailing=false;
const double E3_InpTrailStartR=1.5;
const double E3_InpTrailDistanceR=1;
const ENUM_TIMEFRAMES E3_InpEMA3SignalTimeframe=(ENUM_TIMEFRAMES)16388;
const int E3_InpEMA3StopMode=0; // 0=pivot structure, 1=ATR, 2=signal candle, 3=fixed price distance
const int E3_InpEMA3ATRPeriod=14;
const double E3_InpEMA3StopATR=1.5;
const double E3_InpEMA3SignalBufferATR=0.10;
const double E3_InpEMA3FixedStopPrice=22.5;
const int E3_InpEMA3FastEMA=20;
const int E3_InpEMA3MediumEMA=50;
const double E3_InpAsiaBufferPercent=0.03;
const double E3_InpAMDStopBufferRange=0.03;
const double E3_InpDmCFixedStopPrice=22.5;
const bool E3_InpUseEconomicCalendar=true;
const int E3_InpNewsExpiryMinutes=15;
const double E3_InpNewsStopPrice=9;
const bool E3_InpAllowProvisionalWeekend=false;
const int E3_InpGridLevels=3;
const double E3_InpGridRiskPercent=0.5;
const double E3_InpWeaknessATRImpulse=2;

datetime E3_g_last_bar=0;
long E3_g_last_event_id=0;

bool E3_AAA_SpreadOK()
{
   if(E3_InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(E3_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(E3_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=E3_InpMaxSpreadPoints;
}

bool E3_AAA_LoadRates(const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);
   return CopyRates(E3_Symbol,timeframe,0,count,rates)>=count;
}

void E3_AAA_RunEMA3()
{
   if(E3_InpUseTrailing) E3_AAA_TrailR(E3_Symbol,E3_InpMagic,E3_InpTrailStartR,E3_InpTrailDistanceR);
   ENUM_TIMEFRAMES signal_timeframe=E3_InpEMA3SignalTimeframe;
   if(!E3_AAA_NewBar(E3_Symbol,signal_timeframe,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic)) return;
   MqlRates r[];
   int needed=MathMax(E3_InpPivotBars+3,12);
   if(!E3_AAA_LoadRates(signal_timeframe,needed,r)) return;
   double trend=E3_AAA_MA(E3_Symbol,signal_timeframe,E3_InpTrendEMA,1);
   double trend_old=E3_AAA_MA(E3_Symbol,signal_timeframe,E3_InpTrendEMA,1+E3_InpTrendSlopeBars);
   double fast=E3_AAA_MA(E3_Symbol,signal_timeframe,E3_InpEMA3FastEMA,1);
   double medium=E3_AAA_MA(E3_Symbol,signal_timeframe,E3_InpEMA3MediumEMA,1);
   double atr=E3_AAA_ATR(E3_Symbol,signal_timeframe,E3_InpEMA3ATRPeriod,1);
   if(trend==EMPTY_VALUE || trend_old==EMPTY_VALUE || fast==EMPTY_VALUE || medium==EMPTY_VALUE || atr<=0.0) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<2+E3_InpPivotBars;i++) { prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   MqlTick tick; if(!SymbolInfoTick(E3_Symbol,tick)) return;
   if(r[1].close>prior_high && r[1].close>trend && fast>medium && trend>trend_old && E3_HAMA_SafeRegimeAllowsDirection(1))
     {
      double stop=prior_low;
      if(E3_InpEMA3StopMode==1) stop=tick.ask-E3_InpEMA3StopATR*atr;
      else if(E3_InpEMA3StopMode==2) stop=r[1].low-E3_InpEMA3SignalBufferATR*atr;
      else if(E3_InpEMA3StopMode==3) stop=tick.ask-E3_InpEMA3FixedStopPrice;
      if(stop<tick.ask) E3_AAA_SendMarket(E3_Symbol,1,stop,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,(E3_InpUseMarkovRegimeFilter ? "Safe AAA EMA3" : "AAA EMA3"));
     }
   else if(r[1].close<prior_low && r[1].close<trend && fast<medium && trend<trend_old && E3_HAMA_SafeRegimeAllowsDirection(-1))
     {
      double stop=prior_high;
      if(E3_InpEMA3StopMode==1) stop=tick.bid+E3_InpEMA3StopATR*atr;
      else if(E3_InpEMA3StopMode==2) stop=r[1].high+E3_InpEMA3SignalBufferATR*atr;
      else if(E3_InpEMA3StopMode==3) stop=tick.bid+E3_InpEMA3FixedStopPrice;
      if(stop>tick.bid) E3_AAA_SendMarket(E3_Symbol,-1,stop,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,(E3_InpUseMarkovRegimeFilter ? "Safe AAA EMA3" : "AAA EMA3"));
     }
}

void E3_AAA_RunAsiaBreakout()
{
   if(E3_InpUseTrailing) E3_AAA_TrailR(E3_Symbol,E3_InpMagic,2.0,0.5);
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_H1,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   MqlDateTime utc; TimeToStruct(E3_AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>13) return;
   double high,low;
   if(!E3_AAA_SessionRangeUTC(E3_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_H1,3,r)) return;
   double buffer=(high-low)*E3_InpAsiaBufferPercent;
   double midpoint=(high+low)/2.0;
   if(r[1].close>high+buffer && r[1].low<=high+buffer)
      E3_AAA_SendMarket(E3_Symbol,1,midpoint,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA Asia confirmed retest");
   else if(r[1].close<low-buffer && r[1].high>=low-buffer)
      E3_AAA_SendMarket(E3_Symbol,-1,midpoint,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA Asia confirmed retest");
}

void E3_AAA_RunDmC()
{
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_H1,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   MqlRates day[],hour[];
   if(!E3_AAA_LoadRates(PERIOD_D1,3,day) || !E3_AAA_LoadRates(PERIOD_H1,3,hour)) return;
   double body_high=MathMax(day[1].open,day[1].close);
   double body_low=MathMin(day[1].open,day[1].close);
   MqlTick tick; if(!SymbolInfoTick(E3_Symbol,tick)) return;
   if(hour[1].low<=body_low && hour[1].close>body_low && hour[1].close>hour[1].open)
      E3_AAA_SendMarket(E3_Symbol,1,tick.ask-E3_InpDmCFixedStopPrice,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA DmC body reaction");
   else if(hour[1].high>=body_high && hour[1].close<body_high && hour[1].close<hour[1].open)
      E3_AAA_SendMarket(E3_Symbol,-1,tick.bid+E3_InpDmCFixedStopPrice,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA DmC body reaction");
}

void E3_AAA_RunAMD()
{
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M15,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   MqlDateTime utc; TimeToStruct(E3_AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>11) return;
   double high,low;
   if(!E3_AAA_SessionRangeUTC(E3_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_M15,3,r)) return;
   double range=high-low;
   double sweep_min=range*0.0002;
   double stop_buffer=range*E3_InpAMDStopBufferRange;
   if(r[1].high>high+sweep_min && r[1].close<high)
      E3_AAA_SendMarket(E3_Symbol,-1,r[1].high+stop_buffer,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA AMD London fade");
   else if(r[1].low<low-sweep_min && r[1].close>low)
      E3_AAA_SendMarket(E3_Symbol,1,r[1].low-stop_buffer,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA AMD London fade");
}

void E3_AAA_RunReferencePairOCO()
{
   E3_AAA_ManageOCO(E3_Symbol,E3_InpMagic);
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M15,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   MqlRates eval[]; if(!E3_AAA_LoadRates(PERIOD_M15,3,eval)) return;
   datetime closed_ny=E3_AAA_ToNewYork(eval[1].time);
   MqlDateTime ny; TimeToStruct(closed_ny,ny);
   if(ny.hour!=10 || ny.min!=0) return;
   MqlDateTime refpart=ny; refpart.hour=9; refpart.min=15; refpart.sec=0;
   datetime ref_server=E3_AAA_NewYorkToServer(StructToTime(refpart));
   int shift=iBarShift(E3_Symbol,PERIOD_M15,ref_server,true);
   if(shift<1) return;
   double ref_high=iHigh(E3_Symbol,PERIOD_M15,shift);
   double ref_low=iLow(E3_Symbol,PERIOD_M15,shift);
   double london_high,london_low;
   if(!E3_AAA_SessionRangeNY(E3_Symbol,PERIOD_M15,3,8,london_high,london_low)) return;
   refpart.hour=12; refpart.min=0;
   datetime expiry=E3_AAA_NewYorkToServer(StructToTime(refpart));
   if(expiry<=TimeCurrent()) expiry=TimeCurrent()+60*60;
   double half_risk=E3_InpRiskPercent/2.0;
   if(eval[1].close>eval[1].open && london_high>ref_high && london_high>ref_low)
   {
      E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_SELL_LIMIT,ref_high,london_high,E3_InpRewardRisk,half_risk,E3_InpMagic,expiry,"AAA weakness limit");
      E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_SELL_STOP,ref_low,london_high,E3_InpRewardRisk,half_risk,E3_InpMagic,expiry,"AAA weakness stop");
   }
   else if(eval[1].close<eval[1].open && london_low<ref_low && london_low<ref_high)
   {
      E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_BUY_LIMIT,ref_low,london_low,E3_InpRewardRisk,half_risk,E3_InpMagic,expiry,"AAA weakness limit");
      E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_BUY_STOP,ref_high,london_low,E3_InpRewardRisk,half_risk,E3_InpMagic,expiry,"AAA weakness stop");
   }
}

bool E3_AAA_FindUpcomingPPI(datetime &event_time,long &event_id)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
   {
      // Official BLS release dates inside the requested 2025-08-05 through
      // 2026-08-04 test window. Economic-calendar APIs are unavailable in MT5 tests.
      int dates[10]={20250814,20250910,20251125,20260114,20260130,20260227,20260318,20260414,20260513,20260611};
      int extra_date=20260715;
      datetime now_ny=E3_AAA_ToNewYork(TimeCurrent());
      MqlDateTime p; TimeToStruct(now_ny,p);
      int key=p.year*10000+p.mon*100+p.day;
      bool match=(key==extra_date);
      for(int i=0;i<ArraySize(dates);i++) if(key==dates[i]) { match=true; break; }
      if(!match) return false;
      MqlDateTime release=p; release.hour=8; release.min=30; release.sec=0;
      event_time=E3_AAA_NewYorkToServer(StructToTime(release));
      event_id=key;
      return TimeCurrent()>=event_time-E3_InpNewsExpiryMinutes*60 && TimeCurrent()<=event_time+60;
   }
   if(!E3_InpUseEconomicCalendar) return false;
   MqlCalendarValue values[];
   datetime now=TimeCurrent();
   int total=CalendarValueHistory(values,now-60,now+E3_InpNewsExpiryMinutes*60,NULL,"USD");
   if(total<=0) return false;
   for(int i=0;i<total;i++)
   {
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id,event)) continue;
      if(StringFind(event.name,"Producer Price")<0 && StringFind(event.name,"PPI")<0) continue;
      if(values[i].time>=now-60 && values[i].time<=now+E3_InpNewsExpiryMinutes*60)
      {
         event_time=values[i].time;
         event_id=(long)values[i].event_id;
         return true;
      }
   }
   return false;
}

void E3_AAA_RunNewsPulse()
{
   E3_AAA_ManageOCO(E3_Symbol,E3_InpMagic);
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M1,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   datetime event_time=0; long event_id=0;
   if(!E3_AAA_FindUpcomingPPI(event_time,event_id) || event_id==E3_g_last_event_id) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_M1,4,r)) return;
   double entry_buffer=MathMax(SymbolInfoDouble(E3_Symbol,SYMBOL_POINT)*10,E3_AAA_ATR(E3_Symbol,PERIOD_M1,14,1)*0.10);
   double buy_entry=r[1].high+entry_buffer;
   double sell_entry=r[1].low-entry_buffer;
   datetime expiry=event_time+E3_InpNewsExpiryMinutes*60;
   bool a=E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_BUY_STOP,buy_entry,buy_entry-E3_InpNewsStopPrice,E3_InpRewardRisk,E3_InpRiskPercent/2.0,E3_InpMagic,expiry,"AAA PPI buy");
   bool b=E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_SELL_STOP,sell_entry,sell_entry+E3_InpNewsStopPrice,E3_InpRewardRisk,E3_InpRiskPercent/2.0,E3_InpMagic,expiry,"AAA PPI sell");
   if(a || b) E3_g_last_event_id=event_id;
}

void E3_AAA_RunWeekend()
{
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M15,E3_g_last_bar) || !E3_InpEnableTrading || !E3_InpAllowProvisionalWeekend || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic) || E3_AAA_TradedToday(E3_Symbol,E3_InpMagic)) return;
   MqlDateTime utc; TimeToStruct(E3_AAA_ToUTC(TimeCurrent()),utc);
   if(utc.day_of_week!=5 || utc.hour<19 || utc.hour>21) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_M15,22,r)) return;
   double momentum=r[1].close-r[21].open;
   MqlTick tick; if(!SymbolInfoTick(E3_Symbol,tick)) return;
   if(momentum>0.0) E3_AAA_SendMarket(E3_Symbol,1,tick.ask-30.0,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA weekend momentum");
   else if(momentum<0.0) E3_AAA_SendMarket(E3_Symbol,-1,tick.bid+30.0,E3_InpRewardRisk,E3_InpRiskPercent,E3_InpMagic,"AAA weekend momentum");
}

void E3_AAA_RunXAUGrid()
{
   E3_AAA_ManageOCO(E3_Symbol,E3_InpMagic);
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M15,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic)) return;
   MqlDateTime utc; TimeToStruct(E3_AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<6 || utc.hour>=19) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_M15,16,r)) return;
   double atr=E3_AAA_ATR(E3_Symbol,PERIOD_M15,14,1);
   double rsi=E3_AAA_RSI(E3_Symbol,PERIOD_M15,14,1);
   double adx=E3_AAA_ADX(E3_Symbol,PERIOD_H1,14,1);
   double h1_50=E3_AAA_MA(E3_Symbol,PERIOD_H1,50,1),h1_200=E3_AAA_MA(E3_Symbol,PERIOD_H1,200,1);
   double h1_50_old=E3_AAA_MA(E3_Symbol,PERIOD_H1,50,4);
   double h4_20=E3_AAA_MA(E3_Symbol,PERIOD_H4,20,1),h4_50=E3_AAA_MA(E3_Symbol,PERIOD_H4,50,1),h4_20_old=E3_AAA_MA(E3_Symbol,PERIOD_H4,20,3);
   if(atr<=0.0 || adx<18.0 || adx>50.0) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<=13;i++){ prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   int direction=0;
   if(r[1].close>prior_high && r[1].close>r[1].open && rsi>=55.0 && h1_50>h1_200 && h1_50>h1_50_old && h4_20>=h4_50 && h4_20>h4_20_old) direction=1;
   if(r[1].close<prior_low && r[1].close<r[1].open && rsi<=45.0 && h1_50<h1_200 && h1_50<h1_50_old && h4_20<=h4_50 && h4_20<h4_20_old) direction=-1;
   if(direction==0) return;
   double anchor=(direction>0 ? r[1].high : r[1].low);
   double offsets[3]={0.10,0.35,0.60};
   double deepest=anchor+direction*offsets[2]*atr;
   double common_stop=anchor-direction*1.0*atr;
   datetime expiry=TimeCurrent()+8*60*60;
   int levels=MathMax(1,MathMin(E3_InpGridLevels,3));
   for(int i=0;i<levels;i++)
   {
      double entry=anchor+direction*offsets[i]*atr;
      E3_AAA_SendPending(E3_Symbol,(direction>0 ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP),entry,common_stop,2.0,E3_InpGridRiskPercent/levels,E3_InpMagic,expiry,"AAA XAU grid");
   }
}

void E3_AAA_RunXAUWeakness()
{
   E3_AAA_ManageOCO(E3_Symbol,E3_InpMagic);
   if(!E3_AAA_NewBar(E3_Symbol,PERIOD_M15,E3_g_last_bar) || !E3_InpEnableTrading || !E3_AAA_SpreadOK()) return;
   if(E3_AAA_HasExposure(E3_Symbol,E3_InpMagic)) return;
   MqlRates r[]; if(!E3_AAA_LoadRates(PERIOD_M15,36,r)) return;
   double atr=E3_AAA_ATR(E3_Symbol,PERIOD_M15,14,1);
   if(atr<=0.0) return;
   double tolerance=0.20*atr;
   int first_high=-1,second_high=-1,first_low=-1,second_low=-1;
   for(int newer=4;newer<=16;newer++)
   {
      for(int older=newer+4;older<=MathMin(newer+16,30);older++)
      {
         if(first_high<0 && MathAbs(r[newer].high-r[older].high)<=tolerance){ second_high=newer; first_high=older; }
         if(first_low<0 && MathAbs(r[newer].low-r[older].low)<=tolerance){ second_low=newer; first_low=older; }
      }
   }
   datetime expiry=TimeCurrent()+8*15*60;
   if(first_high>0)
   {
      double resistance=MathMax(r[first_high].high,r[second_high].high);
      double range_low=DBL_MAX; for(int i=1;i<=first_high;i++) range_low=MathMin(range_low,r[i].low);
      double impulse=r[first_high+1].close-r[MathMin(first_high+12,35)].open;
      if(impulse>=E3_InpWeaknessATRImpulse*atr)
         E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_BUY_STOP,resistance+0.05*atr,range_low-0.05*atr,2.0,E3_InpRiskPercent,E3_InpMagic,expiry,"AAA XAU weakness breakout");
   }
   else if(first_low>0)
   {
      double support=MathMin(r[first_low].low,r[second_low].low);
      double range_high=-DBL_MAX; for(int i=1;i<=first_low;i++) range_high=MathMax(range_high,r[i].high);
      double impulse=r[MathMin(first_low+12,35)].open-r[first_low+1].close;
      if(impulse>=E3_InpWeaknessATRImpulse*atr)
         E3_AAA_SendPending(E3_Symbol,ORDER_TYPE_SELL_STOP,support-0.05*atr,range_high+0.05*atr,2.0,E3_InpRiskPercent,E3_InpMagic,expiry,"AAA XAU weakness breakout");
   }
}

int E3_OnInit()
{
   if(!E3_DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   E3_AAA_TesterServerOffsetMode=E3_InpTesterServerClockMode;
   E3_AAA_Trade.SetExpertMagicNumber((ulong)E3_InpMagic);
   E3_AAA_Trade.SetTypeFillingBySymbol(E3_Symbol);
   Print(E3_AAA_STRATEGY_NAME," loaded on ",E3_Symbol,". Trading enabled=",E3_InpEnableTrading,"; risk=",DoubleToString(E3_InpRiskPercent,2),"%.");
   return INIT_SUCCEEDED;
}

void E3_OnTick()
{
   E3_DTS_ManageDynamicTrailing(E3_InpMagic);
   if(E3_AAA_STRATEGY_ID==E3_AAA_ID_EMA3) E3_AAA_RunEMA3();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_ASIA) E3_AAA_RunAsiaBreakout();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_DMC) E3_AAA_RunDmC();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_AMD) E3_AAA_RunAMD();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_US100_WEAKNESS || E3_AAA_STRATEGY_ID==E3_AAA_ID_XAU_US100_PORT) E3_AAA_RunReferencePairOCO();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_NEWS_PULSE) E3_AAA_RunNewsPulse();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_WEEKEND) E3_AAA_RunWeekend();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_XAU_GRID) E3_AAA_RunXAUGrid();
   else if(E3_AAA_STRATEGY_ID==E3_AAA_ID_XAU_WEAKNESS) E3_AAA_RunXAUWeakness();
}



int portfolioCurve=INVALID_HANDLE,portfolioDeals=INVALID_HANDLE;
datetime portfolioMinute=0; double portfolioMin=0,portfolioMax=0;
double portfolioPeak=10000,portfolioDD=0; int maxPositions=0;
long seenUS30=-1,seenUSTEC=-1,seenGold=-1;
bool Active(int i){return InpCase==0||InpCase==i;}
void Audit(){double e=AccountInfoDouble(ACCOUNT_EQUITY); portfolioPeak=MathMax(portfolioPeak,e);portfolioDD=MathMax(portfolioDD,100*(portfolioPeak-e)/portfolioPeak);maxPositions=MathMax(maxPositions,PositionsTotal());datetime m=TimeCurrent()/60*60;
 if(m!=portfolioMinute){if(portfolioMinute>0)FileWrite(portfolioCurve,portfolioMinute,AccountInfoDouble(ACCOUNT_BALANCE),e,portfolioMin,portfolioMax,PositionsTotal());portfolioMinute=m;portfolioMin=e;portfolioMax=e;}else{portfolioMin=MathMin(portfolioMin,e);portfolioMax=MathMax(portfolioMax,e);}}
bool Fresh(string symbol,long &seen){MqlTick t;if(!SymbolInfoTick(symbol,t)||t.time_msc==seen||t.bid<=0||t.ask<=0)return false;seen=t.time_msc;return true;}
void Pump(){
 if(Fresh("US30",seenUS30)&&Active(1))H30_OnTick();
 if(Fresh("USTEC",seenUSTEC)){if(Active(2))H100_OnTick();if(Active(3))N5_OnTick();}
 if(Fresh("XAUUSD",seenGold)){if(Active(4))RV_OnTick();if(Active(5))E3_OnTick();}
 Audit();}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research-only adapter refuses live initialization");return INIT_FAILED;}
 if(InpCase<0||InpCase>5||AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_PARAMETERS_INCORRECT;
 SymbolSelect("US30",true);SymbolSelect("USTEC",true);SymbolSelect("XAUUSD",true);
 string tag="five20261007-case"+IntegerToString(InpCase);
 portfolioCurve=FileOpen(tag+"-curve.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(portfolioCurve==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(portfolioCurve,"minute","balance_next","equity_next","minimum_equity","maximum_equity","positions_next");
 if(Active(1)&&H30_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(2)&&H100_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(3)&&N5_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(4)&&RV_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(5)&&E3_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 EventSetTimer(5);Print("FIVE_INIT case=",InpCase," risk=1% shared native USD account");return INIT_SUCCEEDED;}
void OnTick(){Pump();}
void OnTimer(){Pump();if(Active(1))H30_OnTimer();if(Active(2))H100_OnTimer();Audit();}
void OnDeinit(const int reason){EventKillTimer();if(Active(1))H30_OnDeinit(reason);if(Active(2))H100_OnDeinit(reason);if(Active(3))N5_OnDeinit(reason);if(Active(4))RV_OnDeinit(reason);if(portfolioCurve!=INVALID_HANDLE){if(portfolioMinute>0)FileWrite(portfolioCurve,portfolioMinute,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),portfolioMin,portfolioMax,PositionsTotal());FileClose(portfolioCurve);}}
double OnTester(){
 Audit();HistorySelect(0,TimeCurrent()+86400);string tag="five20261007-case"+IntegerToString(InpCase);
 int f=FileOpen(tag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"ticket","position_id","order","time_msc","magic","symbol","entry","type","volume","price","profit","commission","swap","fee","comment","initial_sl","initial_tp");
 for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;ulong o=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
 FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),o,HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetString(d,DEAL_SYMBOL),HistoryDealGetInteger(d,DEAL_ENTRY),type,HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT),HistoryOrderGetDouble(o,ORDER_SL),HistoryOrderGetDouble(o,ORDER_TP));}FileClose(f);
 Print("FIVE_COMPLETE case=",InpCase," balance=",AccountInfoDouble(ACCOUNT_BALANCE)," measured_dd=",portfolioDD," max_positions=",maxPositions," H30attempted=",H30_attempted," H30accepted=",H30_accepted," H100attempted=",H100_attempted," H100accepted=",H100_accepted);return 0;}

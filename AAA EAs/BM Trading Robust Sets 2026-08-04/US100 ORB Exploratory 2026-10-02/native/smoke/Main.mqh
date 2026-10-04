#include <Trade/Trade.mqh>
input int InpCase=0;
input double InpRiskPercent=1.0;
input datetime InpTradeFrom=D'2021.10.02';
input string InpTag="smoke";
input long InpMagic=10020100;
CTrade trade;
datetime lastBar=0,lastCloseAttempt=0,traceBar=0;
int dayKey=0,usedDay=0,ranges=0,signals=0,entryFails=0,closeFails=0,skips=0;
double rangeHigh=0,rangeLow=0;
int audit=INVALID_HANDLE,trace=INVALID_HANDLE,emaHandle=INVALID_HANDLE;
string Dir="US100ORBExplore20261002\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
double P(int i){return Cases[InpCase][i];}
struct Initial{ulong id;double sl,tp,budget,risk;};
Initial initial[];
datetime BuildTime(int y,int m,int d,int h){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);}
int Sunday(int y,int m,int nth){MqlDateTime x;TimeToStruct(BuildTime(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(nth-1)*7;}
datetime NewYork(datetime server){MqlDateTime x;TimeToStruct(server,x);datetime a=BuildTime(x.year,3,Sunday(x.year,3,2),7),b=BuildTime(x.year,11,Sunday(x.year,11,1),6);return server+((server>=a&&server<b)?-4:-5)*3600;}
int DateKey(datetime server){MqlDateTime x;TimeToStruct(NewYork(server),x);return x.year*10000+x.mon*100+x.day;}
int MinuteNY(datetime server){MqlDateTime x;TimeToStruct(NewYork(server),x);return x.hour*60+x.min;}
bool OwnPosition(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
// Current session endpoint is used, not an assumed regular NY cash close.
bool Session(datetime now,int &until){MqlDateTime x;TimeToStruct(now,x);int seconds=x.hour*3600+x.min*60+x.sec;until=86400;
 for(uint i=0;i<20;i++){datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)x.day_of_week,i,from,to))break;int a=(int)from,b=(int)to;
  if(b>a&&seconds>=a&&seconds<b){until=b;return true;}
  if(b<=a&&(seconds>=a||seconds<b)){until=seconds>=a?86400+(b==0?0:b):b;return true;}}
 return false;}
bool FlatDue(datetime now){if(MinuteNY(now)>=955)return true;if(P(5)<0.5)return false;int until=0;if(!Session(now,until))return false;MqlDateTime x;TimeToStruct(now,x);return x.hour*3600+x.min*60+x.sec>=until-600;}
double Price(double v){double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(v/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
double Lots(ENUM_ORDER_TYPE side,double entry,double stop,double budget){double one=0;if(!OrderCalcProfit(side,_Symbol,1.,entry,stop,one)||MathAbs(one)<=0)return 0;
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(lo<=0||hi<=0||step<=0)return 0;
 double qty=MathFloor((MathMin(hi,budget/MathAbs(one))+1e-12)/step)*step;return qty+1e-12<lo?0:qty;}
void Trace(){if(trace==INVALID_HANDLE||TimeCurrent()<InpTradeFrom)return;datetime t=TimeCurrent(),bar=t-t%60;if(bar==traceBar)return;traceBar=bar;FileWrite(trace,(long)t,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),PositionsTotal());}
void ManageClose(datetime now){ulong ticket;if(!OwnPosition(ticket))return;datetime opened=(datetime)PositionGetInteger(POSITION_TIME);int until=0;
 bool overdue=DateKey(now)!=DateKey(opened)||FlatDue(now);if(!overdue||now-lastCloseAttempt<60||!Session(now,until))return;lastCloseAttempt=now;
 bool ok=trade.PositionClose(ticket);if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("ORBEX_CLOSE_FAIL time=%s retcode=%u",TimeToString(now,TIME_DATE|TIME_SECONDS),trade.ResultRetcode());}}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;if(InpCase<0||InpCase>=ArrayRange(Cases,0)||InpRiskPercent<=0||InpRiskPercent>1||SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)<=0)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 if(P(4)>0){emaHandle=iMA(_Symbol,PERIOD_H1,(int)P(4),0,MODE_EMA,PRICE_CLOSE);if(emaHandle==INVALID_HANDLE)return INIT_FAILED;}
 FolderCreate("US100ORBExplore20261002",FILE_COMMON);
 audit=FileOpen(Dir+Tag()+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(audit==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"epoch","signal_bar","side","range_high","range_low","signal_close","entry_quote","initial_sl","initial_tp","requested_risk","lots","quoted_risk","retcode","h1_close","ema");
 if(!MQLInfoInteger(MQL_OPTIMIZATION)){trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(trace==INVALID_HANDLE)return INIT_FAILED;FileWrite(trace,"epoch","balance","equity","margin","positions");}
 PrintFormat("ORBEX_SPEC symbol=%s digits=%d ticksize=%.8f tickvalue=%.8f lotmin=%.8f lotstep=%.8f lotmax=%.8f stops=%d",_Symbol,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL));
 for(int day=0;day<7;day++)for(uint i=0;i<20;i++){datetime a=0,b=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)day,i,a,b))break;PrintFormat("ORBEX_SESSION weekday=%d from=%d until=%d",day,(int)a,(int)b);}
 return INIT_SUCCEEDED;}
void OnTick(){datetime now=TimeCurrent();ManageClose(now);Trace();if(now<InpTradeFrom)return;
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0||bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(ny.day_of_week<1||ny.day_of_week>5)return;int key=DateKey(now);if(key!=dayKey){dayKey=key;rangeHigh=rangeLow=0;}
 int minute=MinuteNY(now),count=(int)P(0)/5;if(minute<570+(int)P(0)||minute>=(int)P(2)||FlatDue(now))return;
 if(rangeHigh==0){datetime start=BuildTime(ny.year,ny.mon,ny.day,0)+570*60,serverStart=now-(NewYork(now)-start);MqlRates rb[];
  if(CopyRates(_Symbol,PERIOD_M5,serverStart,serverStart+(count-1)*300,rb)!=count)return;
  for(int i=0;i<count;i++)if(rb[i].time!=serverStart+i*300||rb[i].time+300>now)return;
  rangeHigh=rb[0].high;rangeLow=rb[0].low;for(int i=1;i<count;i++){rangeHigh=MathMax(rangeHigh,rb[i].high);rangeLow=MathMin(rangeLow,rb[i].low);}ranges++;}
 if(usedDay==dayKey)return;MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1)return;
 if(DateKey(r[0].time)!=dayKey||MinuteNY(r[0].time)<570+(int)P(0)||r[0].time+300>now)return;
 int side=r[0].close>rangeHigh?1:(r[0].close<rangeLow?-1:0);if(side==0)return;
 usedDay=dayKey;signals++;if((int)P(3)!=0&&side!=(int)P(3)){skips++;return;}
 double h1close=0,ema=0;
 if(P(4)>0){double v[];MqlRates hr[];if(CopyBuffer(emaHandle,0,1,1,v)!=1||CopyRates(_Symbol,PERIOD_H1,1,1,hr)!=1||hr[0].time+3600>now){skips++;return;}
  ema=v[0];h1close=hr[0].close;if((side>0&&h1close<=ema)||(side<0&&h1close>=ema)){skips++;return;}}
 ulong ticket;if(OwnPosition(ticket)){skips++;return;}MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return;}
 double entry=side>0?q.ask:q.bid,stop=Price(side>0?rangeLow:rangeHigh),dist=side*(entry-stop),tp=P(1)>0?Price(entry+side*P(1)*dist):0;
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;int until=0;
 bool valid=dist>0&&(side>0?q.bid-stop>minimum:stop-q.ask>minimum);
 if(tp>0)valid=valid&&(side>0?tp-q.bid>minimum:q.ask-tp>minimum);
 if(!valid||!Session(now,until)){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100,lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop,budget);if(lot<=0){skips++;return;}
 double quoted=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,quoted)){skips++;return;}
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,tp,"ORB exploratory long"):trade.Sell(lot,_Symbol,0,stop,tp,"ORB exploratory short");
 FileWrite(audit,(long)now,(long)r[0].time,side,rangeHigh,rangeLow,r[0].close,entry,stop,tp,budget,lot,MathAbs(quoted),trade.ResultRetcode(),h1close,ema);
 if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE){ulong deal=trade.ResultDeal();if(HistoryDealSelect(deal)){int ix=ArraySize(initial);ArrayResize(initial,ix+1);initial[ix].id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);initial[ix].sl=stop;initial[ix].tp=tp;initial[ix].budget=budget;double p=HistoryDealGetDouble(deal,DEAL_PRICE),v=HistoryDealGetDouble(deal,DEAL_VOLUME),risk=0;if(OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,v,p,stop,risk))initial[ix].risk=MathAbs(risk);}}
 else{entryFails++;PrintFormat("ORBEX_ENTRY_FAIL retcode=%u",trade.ResultRetcode());}}
struct Item{ulong id;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){HistorySelect(0,TimeCurrent());Item rows[];int n=0,boundary=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;if(StringFind(HistoryDealGetString(deal,DEAL_COMMENT),"end of test")>=0)boundary++;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);}
 int f=FileOpen(Dir+Tag()+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)return -10000;
 FileWrite(f,"position_id","module","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 double gp=0,gl=0,net=0;int wins=0,bad=0,carry=0;
 for(int k=0;k<n;k++){int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double p=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;net+=p;if(p>0){gp+=p;wins++;}else gl-=p;
  double sl=ix>=0?initial[ix].sl:0,tp=ix>=0?initial[ix].tp:0,risk=ix>=0?initial[ix].risk:0,budget=ix>=0?initial[ix].budget:0;if(risk<=0||budget<=0)bad++;
  if(DateKey(rows[k].opened)!=DateKey(rows[k].closed))carry++;
  FileWrite(f,rows[k].id,"ORB",(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,sl,tp,budget,risk,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p);}
 FileClose(f);double pf=gl>0?gp/gl:(gp>0?99:0),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
 f=FileOpen(Dir+Tag()+"-net.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);if(f==INVALID_HANDLE)return -10000;
 FileWriteString(f,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"balance_dd_pct\":%.8f,\"entry_fail\":%d,\"close_fail\":%d,\"bad_risk\":%d,\"boundary\":%d,\"carryovers\":%d,\"ranges\":%d,\"signals\":%d,\"skips\":%d}",n,net,pf,n>0?100.0*wins/n:0,dd,TesterStatistics(STAT_BALANCE_DDREL_PERCENT),entryFails,closeFails,bad,boundary,carry,ranges,signals,skips));FileClose(f);
 return n>=100&&net>0?(pf-1)*MathSqrt(n)/(1+dd/10):-1;}
void OnDeinit(const int why){if(audit!=INVALID_HANDLE)FileClose(audit);if(trace!=INVALID_HANDLE)FileClose(trace);if(emaHandle!=INVALID_HANDLE)IndicatorRelease(emaHandle);}

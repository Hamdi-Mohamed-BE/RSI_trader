#include <Trade/Trade.mqh>
input int InpCase=0;
input double InpRiskPercent=1.0;
input datetime InpTradeFrom=D'2021.10.02';
input string InpTag="smoke";
input long InpMagic=10020200;
CTrade trade;
datetime lastBar=0,lastCloseAttempt=0,traceBar=0,lastM1=0;
int dayKey=0,usedDay=0,ranges=0,signals=0,entryFails=0,closeFails=0,skips=0;
double weight=0,mean=0,m2=0;
int audit=INVALID_HANDLE,trace=INVALID_HANDLE,barsFile=INVALID_HANDLE;
string Dir="TierVWAPRaw20261002\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
struct Initial{ulong id;double sl,tp,budget,risk;};
Initial initial[];
datetime BuildTime(int y,int m,int d,int h){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);}
int Sunday(int y,int m,int nth){MqlDateTime x;TimeToStruct(BuildTime(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(nth-1)*7;}
datetime NewYork(datetime server){MqlDateTime x;TimeToStruct(server,x);datetime a=BuildTime(x.year,3,Sunday(x.year,3,2),7),b=BuildTime(x.year,11,Sunday(x.year,11,1),6);return server+((server>=a&&server<b)?-4:-5)*3600;}
int DateKey(datetime server){MqlDateTime x;TimeToStruct(NewYork(server),x);return x.year*10000+x.mon*100+x.day;}
int MinuteNY(datetime server){MqlDateTime x;TimeToStruct(NewYork(server),x);return x.hour*60+x.min;}
bool OwnPosition(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
bool Session(datetime now,int &until){MqlDateTime x;TimeToStruct(now,x);int seconds=x.hour*3600+x.min*60+x.sec;until=86400;
 for(uint i=0;i<20;i++){datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)x.day_of_week,i,from,to))break;int a=(int)from,b=(int)to;
  if(b>a&&seconds>=a&&seconds<b){until=b;return true;}
  if(b<=a&&(seconds>=a||seconds<b)){until=seconds>=a?86400+(b==0?0:b):b;return true;}}
 return false;}
bool FlatDue(datetime now){if(MinuteNY(now)>=930)return true;int until=0;if(!Session(now,until))return false;MqlDateTime x;TimeToStruct(now,x);return x.hour*3600+x.min*60+x.sec>=until-600;}
double Price(double v){double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(v/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
double Lots(ENUM_ORDER_TYPE side,double entry,double stop,double budget){double one=0;if(!OrderCalcProfit(side,_Symbol,1.,entry,stop,one)||MathAbs(one)<=0)return 0;
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(lo<=0||hi<=0||step<=0)return 0;
 double qty=MathFloor((MathMin(hi,budget/MathAbs(one))+1e-12)/step)*step;return qty+1e-12<lo?0:qty;}
void Trace(){if(trace==INVALID_HANDLE||TimeCurrent()<InpTradeFrom)return;datetime t=TimeCurrent(),bar=t-t%60;if(bar==traceBar)return;traceBar=bar;FileWrite(trace,(long)t,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),PositionsTotal());}
void ManageClose(datetime now){ulong ticket;if(!OwnPosition(ticket))return;datetime opened=(datetime)PositionGetInteger(POSITION_TIME);int until=0;
 bool overdue=DateKey(now)!=DateKey(opened)||FlatDue(now);if(!overdue||now-lastCloseAttempt<60||!Session(now,until))return;lastCloseAttempt=now;
 bool ok=trade.PositionClose(ticket);if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE)closeFails++;}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;if(InpCase!=0||InpRiskPercent<=0||InpRiskPercent>1||SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)<=0)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 FolderCreate("TierVWAPRaw20261002",FILE_COMMON);
 audit=FileOpen(Dir+Tag()+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 barsFile=FileOpen(Dir+Tag()+"-bars.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(audit==INVALID_HANDLE||trace==INVALID_HANDLE||barsFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"epoch","signal_bar","side","vwap","sd","signal_high","signal_low","signal_close","entry_quote","initial_sl","initial_tp","requested_risk","lots","quoted_risk","retcode");
 FileWrite(trace,"epoch","balance","equity","margin","positions");
 FileWrite(barsFile,"epoch","high","low","close","tick_volume");
 return INIT_SUCCEEDED;}
bool UpdateVWAP(datetime now){MqlDateTime ny;TimeToStruct(NewYork(now),ny);int key=DateKey(now);
 if(key!=dayKey){dayKey=key;lastM1=0;weight=mean=m2=0;ranges++;}
 datetime anchor=now-(NewYork(now)-(BuildTime(ny.year,ny.mon,ny.day,0)+570*60));
 datetime latest=now-now%60-60;if(latest<anchor)return false;
 MqlRates bars[];int n=CopyRates(_Symbol,PERIOD_M1,lastM1>0?lastM1+60:anchor,latest,bars);if(n<0)return false;
 for(int i=0;i<n;i++){if(bars[i].time<=lastM1||bars[i].time<anchor||bars[i].time+60>now)continue;
  lastM1=bars[i].time;double w=(double)bars[i].tick_volume,p=(bars[i].high+bars[i].low+bars[i].close)/3;
  if(w<=0)continue;double delta=p-mean,newWeight=weight+w;mean+=w/newWeight*delta;m2+=w*delta*(p-mean);weight=newWeight;
  FileWrite(barsFile,(long)bars[i].time,bars[i].high,bars[i].low,bars[i].close,bars[i].tick_volume);}
 return weight>0&&lastM1==latest;}
void OnTick(){datetime now=TimeCurrent();ManageClose(now);Trace();if(now<InpTradeFrom)return;
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0||bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(ny.day_of_week<1||ny.day_of_week>5)return;
 int minute=MinuteNY(now);if(minute<575||minute>=900)return;if(!UpdateVWAP(bar))return;
 if(minute<600||usedDay==dayKey||FlatDue(now))return;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1||r[0].time+300!=bar||DateKey(r[0].time)!=dayKey)return;
 double sd=MathSqrt(MathMax(0,m2/weight));if(sd<=0)return;
 bool buy=r[0].low<=mean-2*sd&&r[0].close>mean-2*sd&&r[0].close<mean;
 bool sell=r[0].high>=mean+2*sd&&r[0].close<mean+2*sd&&r[0].close>mean;
 if(buy==sell)return;int side=buy?1:-1;usedDay=dayKey;signals++;
 ulong ticket;if(OwnPosition(ticket)){skips++;return;}MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return;}
 double entry=side>0?q.ask:q.bid,tp=Price(mean),dist=side*(tp-entry),stop=Price(entry-side*dist);
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;int until=0;
 bool valid=dist>0&&(side>0?q.bid-stop>minimum:stop-q.ask>minimum)&&(side>0?tp-q.bid>minimum:q.ask-tp>minimum);
 if(!valid||!Session(now,until)){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100,lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop,budget);if(lot<=0){skips++;return;}
 double quoted=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,quoted)){skips++;return;}
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,tp,"VWAP raw long"):trade.Sell(lot,_Symbol,0,stop,tp,"VWAP raw short");
 FileWrite(audit,(long)now,(long)r[0].time,side,mean,sd,r[0].high,r[0].low,r[0].close,entry,stop,tp,budget,lot,MathAbs(quoted),trade.ResultRetcode());
 if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE){ulong deal=trade.ResultDeal();if(HistoryDealSelect(deal)){int ix=ArraySize(initial);ArrayResize(initial,ix+1);initial[ix].id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);initial[ix].sl=stop;initial[ix].tp=tp;initial[ix].budget=budget;double p=HistoryDealGetDouble(deal,DEAL_PRICE),v=HistoryDealGetDouble(deal,DEAL_VOLUME),risk=0;if(OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,v,p,stop,risk))initial[ix].risk=MathAbs(risk);}}
 else entryFails++;}

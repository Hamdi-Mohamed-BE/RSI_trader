#include <Trade/Trade.mqh>
input int InpCase=0;
input double InpRiskPercent=0.5;
input datetime InpTradeFrom=D'2025.10.04';
input string InpTag="smoke";
input long InpMagic=10040401;
CTrade trade;
int audit=INVALID_HANDLE,trace=INVALID_HANDLE,barsFile=INVALID_HANDLE;
string Dir="EMAAVWAPRaw20261004\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
int e9=INVALID_HANDLE,e21=INVALID_HANDLE,e50=INVALID_HANDLE,atrh=INVALID_HANDLE;
datetime traceBar=0,lastBar=0,lastDay=0,lastCloseAttempt=0,lastHour=0,signalTime=0,signalExpiry=0;
int usedDay=0,ranges=0,signals=0,entryFails=0,closeFails=0,skips=0,signalSide=0,trend=0,lastTF=0;
double ema9=0,ema21=0,dailyATR=0,avwap=0,signalHigh=0,signalLow=0;
datetime anchor=0;
ulong managedId=0;
double originalVolume=0,originalEntry=0,initialDistance=0;
bool trimmed3=false,trimmed5=false,dailyExit=false;
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
 if(b>a&&seconds>=a&&seconds<b){until=b;return true;}if(b<=a&&(seconds>=a||seconds<b)){until=seconds>=a?86400+(b==0?0:b):b;return true;}}return false;}
double Price(double v){double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(v/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
double Lots(ENUM_ORDER_TYPE side,double entry,double stop,double budget){double one=0;if(!OrderCalcProfit(side,_Symbol,1.,entry,stop,one)||MathAbs(one)<=0)return 0;
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(lo<=0||hi<=0||step<=0)return 0;
 double qty=MathFloor((MathMin(hi,budget/MathAbs(one))+1e-12)/step)*step;return qty+1e-12<lo?0:qty;}
void Trace(){if(trace==INVALID_HANDLE||TimeCurrent()<InpTradeFrom)return;datetime t=TimeCurrent(),bar=t-t%60;if(bar==traceBar)return;traceBar=bar;FileWrite(trace,(long)t,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),PositionsTotal());}
double Buffer(int handle,int shift){double v[];if(CopyBuffer(handle,0,shift,1,v)!=1)return 0;return v[0];}
bool Daily(){datetime day=iTime(_Symbol,PERIOD_D1,0);if(day<=0)return false;if(day==lastDay)return true;
 MqlRates d[];ArraySetAsSeries(d,true);if(CopyRates(_Symbol,PERIOD_D1,0,65,d)!=65)return false;
 double a=Buffer(e9,1),b=Buffer(e21,1),c=Buffer(e50,1),prev=Buffer(e9,2),vol=Buffer(atrh,1);if(a<=0||b<=0||c<=0||prev<=0||vol<=0)return false;
 lastDay=day;ema9=a;ema21=b;dailyATR=vol;ranges++;signalSide=0;lastHour=0;avwap=0;anchor=0;
 trend=a>b&&a>prev&&d[1].close>c?1:(a<b&&a<prev&&d[1].close<c?-1:0);
 ulong ticket;if(OwnPosition(ticket)){int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;if(side*(d[1].close-a)<0)dailyExit=true;}else dailyExit=false;
 if(trend!=0){for(int i=3;i<=60;i++){bool pivot=true;for(int k=1;k<=2;k++){if(trend>0&&(d[i].low>=d[i-k].low||d[i].low>=d[i+k].low))pivot=false;if(trend<0&&(d[i].high<=d[i-k].high||d[i].high<=d[i+k].high))pivot=false;}if(pivot){anchor=d[i].time;break;}}}
 return true;}
bool VWAP(datetime now){datetime hour=iTime(_Symbol,PERIOD_H1,0);if(anchor==0||hour<=0)return false;if(hour==lastHour)return avwap>0;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_H1,anchor,hour-1,r);if(n<=0)return false;double w=0,sum=0;
 for(int i=0;i<n;i++){if(r[i].time<anchor||r[i].time+3600>now)continue;double v=(double)r[i].tick_volume;sum+=v*(r[i].high+r[i].low+r[i].close)/3;w+=v;}
 if(w<=0)return false;avwap=sum/w;lastHour=hour;return true;}
void Manage(datetime now){ulong ticket;if(!OwnPosition(ticket)){managedId=0;dailyExit=false;return;}int until=0;if(!Session(now,until))return;
 if(dailyExit){if(now-lastCloseAttempt<60)return;lastCloseAttempt=now;if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE)closeFails++;return;}
 if(managedId!=(ulong)PositionGetInteger(POSITION_IDENTIFIER)||initialDistance<=0)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double rr=side*((side>0?q.bid:q.ask)-originalEntry)/initialDistance;double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 double cut=MathFloor((originalVolume*.2+1e-12)/step)*step,current=PositionGetDouble(POSITION_VOLUME);
 if(cut+1e-12<lo||current-cut+1e-12<lo)return;
 if((!trimmed3&&rr>=3)||(trimmed3&&!trimmed5&&rr>=5)){if(trade.PositionClosePartial(ticket,cut)&&trade.ResultRetcode()==TRADE_RETCODE_DONE){if(!trimmed3)trimmed3=true;else trimmed5=true;}else closeFails++;}}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;if(InpCase!=0||InpRiskPercent<=0||InpRiskPercent>1||SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)<=0)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 e9=iMA(_Symbol,PERIOD_D1,9,0,MODE_EMA,PRICE_CLOSE);e21=iMA(_Symbol,PERIOD_D1,21,0,MODE_EMA,PRICE_CLOSE);e50=iMA(_Symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);atrh=iATR(_Symbol,PERIOD_D1,14);
 if(e9==INVALID_HANDLE||e21==INVALID_HANDLE||e50==INVALID_HANDLE||atrh==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);FolderCreate("EMAAVWAPRaw20261004",FILE_COMMON);
 audit=FileOpen(Dir+Tag()+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');barsFile=FileOpen(Dir+Tag()+"-bars.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(audit==INVALID_HANDLE||trace==INVALID_HANDLE||barsFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"epoch","signal_bar","signal_expiry","side","anchor","avwap","ema9","ema21","atr","signal_high","signal_low","entry_quote","initial_sl","requested_risk","lots","quoted_risk","retcode");
 FileWrite(trace,"epoch","balance","equity","margin","positions");FileWrite(barsFile,"epoch","side","anchor","avwap","ema9","ema21","atr","signal_high","signal_low","signal_close","trigger","expiry");return INIT_SUCCEEDED;}
void ExportInputs(){ENUM_TIMEFRAMES tfs[2]={PERIOD_D1,PERIOD_H1};string names[2]={"d1","h1"};
 for(int k=0;k<2;k++){MqlRates r[];int n=CopyRates(_Symbol,tfs[k],InpTradeFrom-700*86400,TimeCurrent(),r);int f=FileOpen(Dir+Tag()+"-"+names[k]+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)continue;
 FileWrite(f,"epoch","open","high","low","close","tick_volume");for(int i=0;i<n;i++)FileWrite(f,(long)r[i].time,r[i].open,r[i].high,r[i].low,r[i].close,r[i].tick_volume);FileClose(f);}}
void OnTick(){datetime now=TimeCurrent();if(now<InpTradeFrom)return;if(!Daily())return;Manage(now);Trace();
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);int minute=MinuteNY(now);if(ny.day_of_week<1||ny.day_of_week>5||minute<570||minute>=690){signalSide=0;return;}
 ulong ticket;if(OwnPosition(ticket)||usedDay==DateKey(now))return;if(trend==0||!VWAP(now))return;
 ENUM_TIMEFRAMES tf=minute<585?PERIOD_M1:PERIOD_M5;if(lastTF!=(int)tf){lastTF=(int)tf;lastBar=0;signalSide=0;}int sec=PeriodSeconds(tf);datetime bar=iTime(_Symbol,tf,0);if(bar<=0)return;
 if(bar!=lastBar){lastBar=bar;signalSide=0;MqlRates r[];if(CopyRates(_Symbol,tf,1,1,r)!=1||r[0].time+sec!=bar||MinuteNY(r[0].time)<570||DateKey(r[0].time)!=DateKey(now))return;
 double level=MathAbs(avwap-ema9)<=MathAbs(avwap-ema21)?ema9:ema21;if(MathAbs(avwap-level)>dailyATR*.5)return;double low=MathMin(avwap,level),high=MathMax(avwap,level);
 bool valid=trend>0?r[0].close>r[0].open&&r[0].low<=high+.15*dailyATR&&r[0].low>=low-.5*dailyATR&&r[0].close>high:r[0].close<r[0].open&&r[0].high>=low-.15*dailyATR&&r[0].high<=high+.5*dailyATR&&r[0].close<low;
 if(valid){signalSide=trend;signalTime=r[0].time;signalExpiry=bar+sec;signalHigh=r[0].high;signalLow=r[0].low;FileWrite(barsFile,(long)signalTime,trend,(long)anchor,avwap,ema9,ema21,dailyATR,r[0].high,r[0].low,r[0].close,trend>0?r[0].high:r[0].low,(long)signalExpiry);}}
 if(signalSide==0||now>=signalExpiry)return;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;int side=signalSide;if(side>0?q.bid<=signalHigh:q.bid>=signalLow)return;signalSide=0;signals++;usedDay=DateKey(now);
 double entry=side>0?q.ask:q.bid,stop=Price(side>0?iLow(_Symbol,PERIOD_D1,0):iHigh(_Symbol,PERIOD_D1,0));if(side*(entry-stop)/entry>.025)stop=Price(side>0?signalLow:signalHigh);
 double dist=side*(entry-stop),minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;int until=0;
 if(dist<=0||dist/entry>.025||(side>0?q.bid-stop<=minimum:stop-q.ask<=minimum)||!Session(now,until)){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100,lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop,budget);if(lot<=0){skips++;return;}double quoted=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,quoted)){skips++;return;}
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,0,"EMA AVWAP raw long"):trade.Sell(lot,_Symbol,0,stop,0,"EMA AVWAP raw short");
 FileWrite(audit,(long)now,(long)signalTime,(long)signalExpiry,side,(long)anchor,avwap,ema9,ema21,dailyATR,signalHigh,signalLow,entry,stop,budget,lot,MathAbs(quoted),trade.ResultRetcode());
 if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE){ulong deal=trade.ResultDeal();if(HistoryDealSelect(deal)){int ix=ArraySize(initial);ArrayResize(initial,ix+1);initial[ix].id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);initial[ix].sl=stop;initial[ix].tp=0;initial[ix].budget=budget;double p=HistoryDealGetDouble(deal,DEAL_PRICE),v=HistoryDealGetDouble(deal,DEAL_VOLUME),risk=0;if(OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,v,p,stop,risk))initial[ix].risk=MathAbs(risk);managedId=initial[ix].id;originalEntry=p;originalVolume=v;initialDistance=MathAbs(p-stop);trimmed3=trimmed5=dailyExit=false;}}
 else entryFails++;}

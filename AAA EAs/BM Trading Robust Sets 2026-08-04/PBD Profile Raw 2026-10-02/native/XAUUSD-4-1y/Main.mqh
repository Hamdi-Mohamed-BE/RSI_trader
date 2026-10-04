#include <Trade/Trade.mqh>
input int InpCase=0;
input double InpRiskPercent=1.0;
input datetime InpTradeFrom=D'2025.10.02';
input string InpTag="smoke";
input long InpMagic=10020300;
CTrade trade;
datetime lastBar=0,lastCloseAttempt=0,traceBar=0;
int dayKey=0,ranges=0,signals=0,entryFails=0,closeFails=0,skips=0;
bool triedProfile=false,ready=false,used[3];
double profileLow=0,profileHigh=0,poc=0,val=0,vah=0,centroid=0,netMove=0;
int shape=9;
int audit=INVALID_HANDLE,trace=INVALID_HANDLE,barsFile=INVALID_HANDLE,profileFile=INVALID_HANDLE,inputFile=INVALID_HANDLE;
string Dir="PBDProfileRaw20261002\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
struct Initial{ulong id;double sl,tp,budget,risk;string module;};
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
bool FlatDue(datetime now){if(MinuteNY(now)>=960)return true;int until=0;if(!Session(now,until))return false;MqlDateTime x;TimeToStruct(now,x);return x.hour*3600+x.min*60+x.sec>=until-600;}
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
 FolderCreate("PBDProfileRaw20261002",FILE_COMMON);
 audit=FileOpen(Dir+Tag()+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 barsFile=FileOpen(Dir+Tag()+"-bars.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 profileFile=FileOpen(Dir+Tag()+"-profiles.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 inputFile=FileOpen(Dir+Tag()+"-profile-inputs.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(audit==INVALID_HANDLE||trace==INVALID_HANDLE||barsFile==INVALID_HANDLE||profileFile==INVALID_HANDLE||inputFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"epoch","signal_bar","module","shape","side","poc","val","vah","atr","prior_volume","signal_open","signal_high","signal_low","signal_close","signal_volume","previous_close","entry_quote","initial_sl","initial_tp","requested_risk","lots","quoted_risk","retcode");
 FileWrite(trace,"epoch","balance","equity","margin","positions");
 FileWrite(barsFile,"epoch","open","high","low","close","tick_volume");
 FileWrite(profileFile,"epoch","day","anchor","end","bars","low","high","poc","val","vah","centroid","net_move","shape","volume");
 FileWrite(inputFile,"day","epoch","open","high","low","close","tick_volume","real_volume");
 return INIT_SUCCEEDED;}
bool BuildProfile(datetime now){int minute=MinuteNY(now);datetime end=now-(minute-630)*60-now%60,start=end-3600;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_M1,start,end-1,r);if(n!=60)return false;
 double lo=DBL_MAX,hi=-DBL_MAX,total=0;
 for(int i=0;i<n;i++){if(r[i].time!=start+i*60||r[i].tick_volume<=0)return false;lo=MathMin(lo,r[i].low);hi=MathMax(hi,r[i].high);}
 if(hi<=lo)return false;double width=(hi-lo)/64,bins[64];ArrayInitialize(bins,0);
 for(int i=0;i<n;i++){double w=(double)r[i].tick_volume;total+=w;
  FileWrite(inputFile,dayKey,(long)r[i].time,r[i].open,r[i].high,r[i].low,r[i].close,r[i].tick_volume,r[i].real_volume);
  if(r[i].high<=r[i].low){int j=(int)MathFloor((r[i].close-lo)/width);j=MathMax(0,MathMin(63,j));bins[j]+=w;}
  else for(int j=0;j<64;j++){double overlap=MathMax(0.,MathMin(r[i].high,lo+(j+1)*width)-MathMax(r[i].low,lo+j*width));bins[j]+=w*overlap/(r[i].high-r[i].low);}}
 int p=0;double weighted=0;for(int j=0;j<64;j++){if(bins[j]>bins[p])p=j;weighted+=bins[j]*(j+.5)/64;}
 int left=p,right=p;double covered=bins[p];
 while(covered<total*.70&&(left>0||right<63)){double below=left>0?bins[left-1]:-1,above=right<63?bins[right+1]:-1;
  if(above>=below&&right<63){right++;covered+=bins[right];}else{left--;covered+=bins[left];}}
 profileLow=lo;profileHigh=hi;poc=lo+(p+.5)*width;val=lo+left*width;vah=lo+(right+1)*width;
 centroid=weighted/total;netMove=(r[59].close-r[0].open)/(hi-lo);double pos=(p+.5)/64;shape=9;
 if(pos>=.65&&centroid>=.60&&netMove>=.25)shape=1;
 else if(pos<=.35&&centroid<=.40&&netMove<=-.25)shape=-1;
 else if(pos>=.35&&pos<=.65&&centroid>=.40&&centroid<=.60&&MathAbs(netMove)<=.25)shape=0;
 ranges++;FileWrite(profileFile,(long)now,dayKey,(long)start,(long)end,n,lo,hi,poc,val,vah,centroid,netMove,shape,total);
 return true;}
string ModuleName(int module){return module==1?"RECLAIM":(module==2?"WEAK_FADE":"BREAKOUT");}
void OnTick(){datetime now=TimeCurrent();ManageClose(now);Trace();if(now<InpTradeFrom)return;
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0||bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(StringFind(_Symbol,"BTC")<0&&(ny.day_of_week<1||ny.day_of_week>5))return;
 int minute=MinuteNY(now);if(minute<630||minute>=930)return;
 if(dayKey!=DateKey(now)){dayKey=DateKey(now);triedProfile=false;ready=false;for(int j=0;j<3;j++)used[j]=false;}
 if(!triedProfile){triedProfile=true;ready=BuildProfile(bar);}if(!ready)return;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,22,r)!=22||r[21].time+300!=bar)return;
 // CopyRates physical order is oldest -> newest. Export each input once for independent reconstruction.
 for(int j=0;j<22;j++)FileWrite(barsFile,(long)r[j].time,r[j].open,r[j].high,r[j].low,r[j].close,r[j].tick_volume);
 if(minute<635||shape==9||r[21].time<bar-(minute-630)*60)return;
 double atr=0,priorVolume=0;
 for(int j=7;j<=20;j++)atr+=MathMax(r[j].high-r[j].low,MathMax(MathAbs(r[j].high-r[j-1].close),MathAbs(r[j].low-r[j-1].close)))/14;
 for(int j=1;j<=20;j++)priorVolume+=(double)r[j].tick_volume/20;
 if(atr<=0||priorVolume<=0)return;ulong ticket;if(OwnPosition(ticket)||FlatDue(now))return;
 bool inside=r[21].close>val&&r[21].close<vah,bull=r[21].close>r[21].open,bear=r[21].close<r[21].open;
 int mask=(int)Cases[InpCase][0];
 for(int module=1;module<=3;module++){if((mask!=4&&mask!=module)||used[module-1])continue;bool buy=false,sell=false;
  if(module==1){buy=(shape==1||shape==0)&&r[21].low<val&&inside&&bull;sell=(shape==-1||shape==0)&&r[21].high>vah&&inside&&bear;}
  else if(module==2){buy=shape==-1&&r[21].low<val&&inside&&bull&&r[21].tick_volume<=priorVolume;sell=shape==1&&r[21].high>vah&&inside&&bear&&r[21].tick_volume<=priorVolume;}
  else{bool previousInside=r[20].close>=val&&r[20].close<=vah,strong=r[21].tick_volume>=1.5*priorVolume;
   buy=(shape==1||shape==0)&&previousInside&&strong&&bull&&r[21].close>vah+.1*atr&&r[21].close-r[21].open>=.5*atr;
   sell=(shape==-1||shape==0)&&previousInside&&strong&&bear&&r[21].close<val-.1*atr&&r[21].open-r[21].close>=.5*atr;}
  if(buy==sell)continue;int side=buy?1:-1;MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;continue;}
  double entry=side>0?q.ask:q.bid,stop=0,tp=0;
  if(module==3){stop=Price(side>0?val-.1*atr:vah+.1*atr);tp=Price(entry+side*2*side*(entry-stop));}
  else{stop=Price(side>0?r[21].low-.1*atr:r[21].high+.1*atr);tp=Price(module==2?poc:(side>0?vah:val));}
  double dist=side*(entry-stop),reward=side*(tp-entry),minimum=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;int until=0;
  bool valid=dist>0&&reward>0&&dist>=3*(q.ask-q.bid)&&(side>0?q.bid-stop>minimum:stop-q.ask>minimum)&&(side>0?tp-q.bid>minimum:q.ask-tp>minimum);
  if(!valid||!Session(now,until)){skips++;continue;}
  double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100,lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop,budget);if(lot<=0){skips++;continue;}
  double quoted=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,quoted)){skips++;continue;}
  used[module-1]=true;signals++;bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,tp,"PBD "+ModuleName(module)):trade.Sell(lot,_Symbol,0,stop,tp,"PBD "+ModuleName(module));
  FileWrite(audit,(long)now,(long)r[21].time,module,shape,side,poc,val,vah,atr,priorVolume,r[21].open,r[21].high,r[21].low,r[21].close,r[21].tick_volume,r[20].close,entry,stop,tp,budget,lot,MathAbs(quoted),trade.ResultRetcode());
  if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE){ulong deal=trade.ResultDeal();if(HistoryDealSelect(deal)){int ix=ArraySize(initial);ArrayResize(initial,ix+1);initial[ix].id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);initial[ix].sl=stop;initial[ix].tp=tp;initial[ix].budget=budget;initial[ix].module=ModuleName(module);double p=HistoryDealGetDouble(deal,DEAL_PRICE),v=HistoryDealGetDouble(deal,DEAL_VOLUME),risk=0;if(OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,v,p,stop,risk))initial[ix].risk=MathAbs(risk);}}
  else entryFails++;return;}}
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
  FileWrite(f,rows[k].id,ix>=0?initial[ix].module:"UNKNOWN",(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,sl,tp,budget,risk,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p);}
 FileClose(f);double pf=gl>0?gp/gl:(gp>0?99:0),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
 f=FileOpen(Dir+Tag()+"-net.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);if(f==INVALID_HANDLE)return -10000;
 FileWriteString(f,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"balance_dd_pct\":%.8f,\"entry_fail\":%d,\"close_fail\":%d,\"bad_risk\":%d,\"boundary\":%d,\"carryovers\":%d,\"ranges\":%d,\"signals\":%d,\"skips\":%d}",n,net,pf,n>0?100.0*wins/n:0,dd,TesterStatistics(STAT_BALANCE_DDREL_PERCENT),entryFails,closeFails,bad,boundary,carry,ranges,signals,skips));FileClose(f);
 return n>=100&&net>0?(pf-1)*MathSqrt(n)/(1+dd/10):-1;}

void OnDeinit(const int why){if(audit!=INVALID_HANDLE)FileClose(audit);if(trace!=INVALID_HANDLE)FileClose(trace);if(barsFile!=INVALID_HANDLE)FileClose(barsFile);if(profileFile!=INVALID_HANDLE)FileClose(profileFile);if(inputFile!=INVALID_HANDLE)FileClose(inputFile);}

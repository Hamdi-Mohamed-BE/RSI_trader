double Cases[][10]={
{0.0,15.0,2.0,0.0,0.0,0.0,0.0,0.0,0.0,1200.0},
{0.0,15.0,2.0,0.0,1.25,0.0,0.0,0.0,0.0,1200.0},
{0.0,30.0,1.0,0.0,1.25,0.0,0.0,1.0,0.0,1200.0},
{1.0,15.0,2.0,0.0,1.25,0.0,0.0,0.0,0.0,1200.0},
{1.0,5.0,2.0,0.0,1.25,0.05,0.25,0.0,0.0,1200.0},
{2.0,15.0,2.0,0.0,1.25,0.0,0.0,0.0,0.0,1200.0},
{2.0,30.0,3.0,0.0,1.25,0.05,0.25,1.0,0.0,1200.0}
};
#property strict
#property description "Research-only ATR/RVOL/Markov ORB breakout and failed-breakout reversal"
#include <Trade/Trade.mqh>
input int InpCase=0;
input string InpTag="orb-regime-research";
input bool InpVerbose=false;
input double InpRiskPct=1.0;
const int MAGIC=26100782;
CTrade trade;
int module=0,range_minutes=15,markov=0,cutoff=1200;
double target_r=2,stop_atr=0,rvol_min=0,range_min=0,range_max=0,trail_atr=0;
int d_atr=INVALID_HANDLE,m_atr=INVALID_HANDLE,eqfile=INVALID_HANDLE,qfile=INVALID_HANDLE,df=INVALID_HANDLE;
datetime minute=0,lastbar=0,dayutc=0;
long ticks=0;
int failed=0,updates=0,day=0,range_count=0,warmup_skips=0,minimum_skips=0,filter_skips=0,route=0;
double hi=0,lo=0,openvol=0,rvol=0,previous_close=0,excursion_hi=0,excursion_lo=0,entryrisk=0,entryprice=0;
bool ready=false,traded=false,seen_up=false,seen_down=false,range_ok=false;
double volumes[20];int volcount=0,volnext=0;bool seeded=false;
int state=1;double p_bear=0,p_side=1,p_bull=0,signal=0;
string Tag(){return InpTag+"-"+(string)InpCase;}
int Sunday(int y,int m,int n){MqlDateTime d={};d.year=y;d.mon=m;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+7*(n-1);}
int NYOffset(datetime utc){MqlDateTime d,x={};TimeToStruct(utc,d);x.year=d.year;x.mon=3;x.day=Sunday(d.year,3,2);x.hour=7;datetime a=StructToTime(x);x.mon=11;x.day=Sunday(d.year,11,1);x.hour=6;return utc>=a && utc<StructToTime(x)?-4:-5;}
int HHMM(datetime utc){MqlDateTime d;TimeToStruct(utc+NYOffset(utc)*3600,d);return d.hour*100+d.min;}
double Price(double v){double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(v/step)*step,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
bool OurPosition(ulong &ticket){ticket=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC){ticket=t;return true;}}return false;}
double ATR(int handle){double v[];return CopyBuffer(handle,0,1,1,v)==1?v[0]:0;}
int Regime(double value){return value>0.02?2:(value<-.02?0:1);}
void DailyRegime(datetime now){
 // Completed broker D1 bars only (broker clock explicitly assumed UTC).
 // Matrix uses 1000 past observations and additive Laplace smoothing.
 MqlRates d[];int n=CopyRates(_Symbol,PERIOD_D1,1,1021,d);
 if(n<272){state=1;p_bear=0;p_side=1;p_bull=0;signal=0;warmup_skips++;return;}
 double counts[3][3];for(int a=0;a<3;a++)for(int b=0;b<3;b++)counts[a][b]=1;
 int prev=Regime(d[20].close/d[0].close-1);
 for(int i=21;i<n;i++){int s=Regime(d[i].close/d[i-20].close-1);counts[prev][s]++;prev=s;}
 state=prev;double total=counts[state][0]+counts[state][1]+counts[state][2];
 p_bear=counts[state][0]/total;p_side=counts[state][1]/total;p_bull=counts[state][2]/total;signal=p_bull-p_bear;
}
void SeedVolume(datetime now){
 if(seeded)return;seeded=true;
 MqlDateTime x;TimeToStruct(now+NYOffset(now)*3600,x);x.hour=0;x.min=0;x.sec=0;datetime localday=StructToTime(x);
 // Seed using only earlier complete NY opening windows. No current/future rows.
 for(int ago=45;ago>=1;ago--){
  datetime ld=localday-ago*86400,begin=ld+570*60-NYOffset(ld+12*3600)*3600;
  MqlRates old[];int n=CopyRates(_Symbol,PERIOD_M5,begin,begin+range_minutes*60-1,old);
  if(n!=range_minutes/5)continue;
  double volume=0;for(int i=0;i<n;i++)volume+=(double)old[i].tick_volume;
  if(volume<=0)continue;volumes[volnext]=volume;volnext=(volnext+1)%20;volcount=MathMin(20,volcount+1);
 }
}
void Log(string reason,MqlRates &bar,double sl=0,double tp=0,double qty=0,double budget=0,double loss=0){
 if(df==INVALID_HANDLE)return;
 FileWrite(df,(long)TimeCurrent(),(long)bar.time,reason,route,hi,lo,rvol,ATR(d_atr),state,p_bear,p_side,p_bull,signal,bar.close,sl,tp,qty,budget,loss,trade.ResultRetcode());
}
void Snapshot(){ticks++;datetime now=TimeCurrent();if(eqfile!=INVALID_HANDLE && now/60!=minute){minute=now/60;FileWrite(eqfile,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}}
void Reset(datetime now){
 MqlDateTime ny;TimeToStruct(now+NYOffset(now)*3600,ny);day=ny.year*10000+ny.mon*100+ny.day;
 hi=0;lo=0;openvol=0;range_count=0;ready=false;traded=false;seen_up=false;seen_down=false;range_ok=false;
 previous_close=0;excursion_hi=0;excursion_lo=0;entryrisk=0;entryprice=0;
 SeedVolume(now);DailyRegime(now);route=module==2?(state==1 && p_side>=.5?1:0):module;
}
void Lock(MqlRates &bar){
 ready=true;double avg=0;for(int i=0;i<volcount;i++)avg+=volumes[i];if(volcount>0)avg/=volcount;
 rvol=avg>0?openvol/avg:0;double da=ATR(d_atr),normal=da>0?(hi-lo)/da:0;
 range_ok=hi>lo && da>0;
 if(rvol_min>0 && (volcount<14 || rvol<rvol_min))range_ok=false;
 if(range_min>0 && normal<range_min)range_ok=false;
 if(range_max>0 && normal>range_max)range_ok=false;
 volumes[volnext]=openvol;volnext=(volnext+1)%20;volcount=MathMin(20,volcount+1);
 Log(range_ok?"range_ready":"range_filter_skip",bar);
}
void Enter(int dir,MqlRates &bar,int kind){
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double ep=dir>0?tick.ask:tick.bid,ma=ATR(m_atr),da=ATR(d_atr);
 double sl=kind==0?(dir>0?lo:hi):(dir>0?MathMin(excursion_lo,bar.low)-.1*ma:MathMax(excursion_hi,bar.high)+.1*ma);
 if(stop_atr>0)sl=ep+(dir>0?-1:1)*stop_atr*da;
 sl=Price(sl);double dist=MathAbs(ep-sl);
 double tp=kind==1?(dir>0?hi:lo):ep+(dir>0?1:-1)*target_r*dist;tp=Price(tp);
 double min_dist=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((dir>0 && (sl>=tick.bid-min_dist || tp<=tick.bid+min_dist)) || (dir<0 && (sl<=tick.ask+min_dist || tp>=tick.ask-min_dist)) || dist<=0){filter_skips++;Log("invalid_stop_skip",bar,sl,tp);return;}
 double money=0,budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100;
 if(!OrderCalcProfit(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1,ep,sl,money) || money>=0){failed++;Log("sizing_error",bar,sl,tp);return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),qty=NormalizeDouble(MathFloor(budget/-money/step+1e-9)*step,8);
 qty=MathMin(qty,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(qty<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){minimum_skips++;Log("minimum_lot_skip",bar,sl,tp,qty,budget,-money);return;}
 bool ok=dir>0?trade.Buy(qty,_Symbol,0,sl,tp,"Research ORB breakout/reversal"):trade.Sell(qty,_Symbol,0,sl,tp,"Research ORB breakout/reversal");
 traded=true;if(ok){entryrisk=dist;entryprice=trade.ResultPrice();}else failed++;
 Log(ok?(kind==0?"breakout_entry":"reversal_entry"):"entry_failed",bar,sl,tp,qty,budget,-money);
}
void Manage(){
 ulong t;if(!OurPosition(t))return;
 if(HHMM(TimeCurrent())>=1555){if(!trade.PositionClose(t))updates++;return;}
 if(trail_atr<=0 || entryrisk<=0)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
 double px=buy?q.bid:q.ask,ep=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),ma=ATR(m_atr);
 if((buy?px-ep:ep-px)<entryrisk || ma<=0)return;
 double next=Price(px+(buy?-1:1)*trail_atr*ma);
 double min_dist=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((buy && next>sl+_Point && px-next>min_dist) || (!buy && next<sl-_Point && next-px>min_dist))if(!trade.PositionModify(t,next,tp))updates++;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0))return INIT_PARAMETERS_INCORRECT;
 module=(int)Cases[InpCase][0];range_minutes=(int)Cases[InpCase][1];target_r=Cases[InpCase][2];stop_atr=Cases[InpCase][3];rvol_min=Cases[InpCase][4];range_min=Cases[InpCase][5];range_max=Cases[InpCase][6];markov=(int)Cases[InpCase][7];trail_atr=Cases[InpCase][8];cutoff=(int)Cases[InpCase][9];
 if(range_minutes!=5 && range_minutes!=15 && range_minutes!=30)return INIT_PARAMETERS_INCORRECT;
 d_atr=iATR(_Symbol,PERIOD_D1,14);m_atr=iATR(_Symbol,PERIOD_M5,14);if(d_atr==INVALID_HANDLE || m_atr==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(MAGIC);trade.SetTypeFillingBySymbol(_Symbol);
 if(InpVerbose){
  eqfile=FileOpen(Tag()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');qfile=FileOpen(Tag()+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');df=FileOpen(Tag()+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  if(eqfile==INVALID_HANDLE || qfile==INVALID_HANDLE || df==INVALID_HANDLE)return INIT_FAILED;
  FileWrite(eqfile,"epoch","balance","equity");FileWrite(qfile,"deal","position_id","epoch","entry","bid","ask","volume","spread_cash");
  FileWrite(df,"epoch","bar_epoch","reason","module","range_high","range_low","rvol","daily_atr","regime","p_bear","p_sideways","p_bull","signal","close","sl","tp","lots","risk_budget","unit_loss","retcode");
 }
 return INIT_SUCCEEDED;
}
void OnTick(){
 Snapshot();Manage();
 MqlRates bars[];if(CopyRates(_Symbol,PERIOD_M5,1,1,bars)!=1 || bars[0].time==lastbar)return;
 MqlRates b=bars[0];lastbar=b.time;MqlDateTime ny;TimeToStruct(b.time+NYOffset(b.time)*3600,ny);int d=ny.year*10000+ny.mon*100+ny.day;
 if(d!=day)Reset(b.time);
 if(ny.day_of_week==0 || ny.day_of_week==6)return;
 int mins=ny.hour*60+ny.min;
 if(mins>=570 && mins<570+range_minutes){
  if(range_count==0){hi=b.high;lo=b.low;}else{hi=MathMax(hi,b.high);lo=MathMin(lo,b.low);}
  range_count++;openvol+=(double)b.tick_volume;previous_close=b.close;
  if(range_count==range_minutes/5)Lock(b);return;
 }
 if(!ready || !range_ok || traded || HHMM(TimeCurrent())>=cutoff)return;
 ulong t;if(OurPosition(t))return;
 if(module==2)route=(state==1 && p_side>=.5)?1:0;
 int dir=0;
 if(route==0){
  dir=b.close>hi?1:(b.close<lo?-1:0);
  if(markov && dir!=0 && ((dir>0 && signal<=0) || (dir<0 && signal>=0)))dir=0;
 }else{
  if(markov && !(state==1 && p_side>=.5))return;
  if(seen_up && previous_close>hi && b.close<=hi && b.close>lo)dir=-1;
  if(seen_down && previous_close<lo && b.close>=lo && b.close<hi)dir=1;
 }
 if(dir!=0)Enter(dir,b,route);
 if(b.close>hi){seen_up=true;excursion_hi=MathMax(excursion_hi,b.high);}
 if(b.close<lo){seen_down=true;excursion_lo=excursion_lo>0?MathMin(excursion_lo,b.low):b.low;}
 previous_close=b.close;
}
double OnTester(){
 HistorySelect(0,TimeCurrent());int out=FileOpen(Tag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
 FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=MAGIC)continue;
  ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
  FileWrite(out,deal,HistoryDealGetInteger(deal,DEAL_POSITION_ID),(long)HistoryDealGetInteger(deal,DEAL_TIME),HistoryDealGetInteger(deal,DEAL_ENTRY),HistoryDealGetInteger(deal,DEAL_TYPE),HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP));
 }
 FileClose(out);out=FileOpen(Tag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;ulong t;
 FileWrite(out,"net","equity_dd","balance_dd","failed_entries","failed_updates","market_closed_updates","balance","open_position","last_quote_epoch","ticks","mt5_sharpe","trades","minimum_lot_skips","filter_skips");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),failed,updates,0,AccountInfoDouble(ACCOUNT_BALANCE),(int)OurPosition(t),(long)TimeCurrent(),ticks,TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_TRADES),minimum_skips,filter_skips);FileClose(out);
 if(eqfile!=INVALID_HANDLE){FileWrite(eqfile,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileFlush(eqfile);}
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(qfile==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal) || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=MAGIC)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double qty=HistoryDealGetDouble(trans.deal,DEAL_VOLUME),cash=0;ENUM_ORDER_TYPE kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE)==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 bool ok=OrderCalcProfit(kind,_Symbol,qty,tick.bid,tick.ask,cash);
 FileWrite(qfile,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),HistoryDealGetInteger(trans.deal,DEAL_ENTRY),tick.bid,tick.ask,qty,ok?MathAbs(cash):-1);
}
void OnDeinit(const int reason){if(eqfile!=INVALID_HANDLE)FileClose(eqfile);if(qfile!=INVALID_HANDLE)FileClose(qfile);if(df!=INVALID_HANDLE)FileClose(df);if(d_atr!=INVALID_HANDLE)IndicatorRelease(d_atr);if(m_atr!=INVALID_HANDLE)IndicatorRelease(m_atr);}

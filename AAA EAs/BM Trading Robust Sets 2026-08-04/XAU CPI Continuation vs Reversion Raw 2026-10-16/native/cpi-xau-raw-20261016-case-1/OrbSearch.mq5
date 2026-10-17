double Cases[][2]={{1,0}};
long Events[]={1579008600,1581600600,1583929800,1586521800,1589286600,1591792200,1594729800,1597235400,1599827400,1602592200,1605187800,1607607000,1610544600,1612963800,1615383000,1618317000,1620822600,1623328200,1626179400,1628685000,1631622600,1634128200,1636551000,1639143000,1641994200,1644499800,1646919000,1649766600,1652272200,1654864200,1657715400,1660134600,1663072200,1665664200,1668087000,1670938200,1673530200,1676381400,1678797000,1681302600,1683721800,1686659400,1689165000,1691670600,1694608200,1697113800,1699968600,1702387800,1704979800,1707831000,1710246600,1712752200,1715776200,1718195400,1720701000,1723638600,1726057800,1728563400,1731504600,1733923800,1736947800,1739367000,1741782600,1744288200,1747139400,1749645000,1752582600,1755001800,1757593800,1761309000,1766064600,1768311000,1770989400,1773232200,1775824200,1778589000,1781094600,1784032200,1786537800,1789129800,1791981000};
string Kinds[]={"CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI","CPI"};
#property strict
#property description "TESTER ONLY: release-aligned CPI continuation versus midpoint/anchor reversion"
#include <Trade/Trade.mqh>
input int InpCase=0;
input string InpTag="xau-cpi-raw";
input bool InpVerbose=false;
input double InpRiskPct=0.25;

// build_engine.py prepends the immutable Cases, Events and Kinds arrays.
// Mode 0: continuation 1.5R; mode 1: anchor fade, minimum 1.5R;
// mode 2: labelled anchor-fade diagnostic without that minimum.
// No live trading, trailing, break-even, partial exits, or parameter search.
const int MAGIC=26101684;
CTrade trade;
int eqfile=INVALID_HANDLE,qfile=INVALID_HANDLE,df=INVALID_HANDLE;
int strategy_mode=0,next_event=0,event_index=-1,spike=0;
int failed=0,updates=0,closed_rejections=0,minimum_skips=0,filter_skips=0,events_seen=0;
int zero_spread_entry_quotes=0;
long ticks=0,minute=-1;
datetime last_closed_bar=0,last_rejected_close=0;
bool active=false,handled=false,have_impulse=false,positive_spread=false,have_previous_quote=false;
double fair=0,pre_atr=0,first_close=0,spike_high=0,spike_low=0,midpoint=0,previous_close=0;
double request_bid=0,request_ask=0;
MqlTick previous_quote,pre_quote;

string Tag(){return InpTag+"-"+(string)InpCase;}
double TickSize(){return SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);}
double Price(double value,int rounding=0){
 double step=TickSize();
 double units=value/step;
 double rounded=rounding<0?MathFloor(units+1e-9):(rounding>0?MathCeil(units-1e-9):MathRound(units));
 return NormalizeDouble(rounded*step,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
long QuoteMsc(MqlTick &quote){return quote.time_msc>0?quote.time_msc:(long)quote.time*1000;}
bool OurPosition(ulong &ticket){
 ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--){
  ulong candidate=PositionGetTicket(i);
  if(candidate==0)continue;
  if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC){ticket=candidate;return true;}
 }
 return false;
}
void Log(string reason,MqlRates &bar,double sl=0,double tp=0,double qty=0,double budget=0,double unit_loss=0,string info="",double entry_rr=0){
 if(df==INVALID_HANDLE)return;
 MqlTick quote={};SymbolInfoTick(_Symbol,quote);
 // Keep the existing raw-runner schema first; append all new audit fields.
 FileWrite(df,(long)TimeCurrent(),event_index,event_index>=0?Events[event_index]:0,event_index>=0?Kinds[event_index]:"",reason,
  (long)bar.time,bar.open,bar.high,bar.low,bar.close,fair,pre_atr,spike,first_close,0,0,0,
  sl,tp,qty,budget,unit_loss,quote.bid,quote.ask,trade.ResultRetcode(),strategy_mode,(int)positive_spread,
  spike_high,spike_low,midpoint,(long)pre_quote.time,pre_quote.bid,pre_quote.ask,info,entry_rr,request_bid,request_ask);
}
void Skip(string reason,MqlRates &bar,string info=""){
 handled=true;filter_skips++;Log(reason,bar,0,0,0,0,0,info);
}
void Snapshot(bool force=false){
 datetime now=TimeCurrent();
 bool near_event=active || (next_event<ArraySize(Events) && now>=Events[next_event]-60 && now<Events[next_event]+3600);
 if(eqfile!=INVALID_HANDLE && (force || (near_event && now/60!=minute))){
  minute=now/60;FileWrite(eqfile,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
 }
}
void StartEvent(int index,MqlTick &quote){
 event_index=index;active=true;handled=false;have_impulse=false;spike=0;
 fair=0;pre_atr=0;first_close=0;spike_high=0;spike_low=0;midpoint=0;previous_close=0;request_bid=0;request_ask=0;
 last_closed_bar=0;ZeroMemory(pre_quote);events_seen++;
 MqlRates empty={};datetime event=(datetime)Events[index];
 if(have_previous_quote)pre_quote=previous_quote;
 Log("event_start",empty);
 long pre_age=(long)event*1000-QuoteMsc(pre_quote);
 if(!have_previous_quote || pre_quote.time>=event || pre_age<0 || pre_age>2000 || pre_quote.bid<=0 || pre_quote.ask<pre_quote.bid){
  Skip("pre_event_quote_missing_or_stale",empty,"last quote must precede release by at most 2000ms");return;
 }
 long first_age=QuoteMsc(quote)-(long)event*1000;
 if(first_age<0 || first_age>2000){Skip("initial_post_event_quote_stale",empty,"first post-release quote later than 2000ms");return;}
 MqlRates before[];
 // CopyRates stores physical array data oldest first. The extra oldest bar
 // supplies the previous close for the first of the 14 true ranges.
 if(CopyRates(_Symbol,PERIOD_M1,event-900,event-1,before)!=15){Skip("missing_exact_pre_news_15_bars",empty);return;}
 for(int i=0;i<15;i++){
  if(before[i].time!=event-900+i*60 || before[i].high<before[i].low || before[i].low<=0){
   Skip("noncontiguous_or_invalid_pre_news_bars",before[i]);return;
  }
 }
 fair=before[14].close;
 for(int i=1;i<15;i++){
  double tr=MathMax(before[i].high-before[i].low,MathMax(MathAbs(before[i].high-before[i-1].close),MathAbs(before[i].low-before[i-1].close)));
  pre_atr+=tr/14.0;
 }
 if(pre_atr<=0 || !MathIsValidNumber(pre_atr)){Skip("pre_news_atr_unavailable",before[14]);return;}
 Log("pre_event_reference_confirmed",before[14],0,0,0,0,0,"simple mean of 14 M1 true ranges; all end strictly before release");
}
void Manage(){
 ulong ticket;if(!OurPosition(ticket))return;
 datetime now=TimeCurrent(),filled=(datetime)PositionGetInteger(POSITION_TIME);
 datetime deadline=filled+(strategy_mode==0?900:1800);
 if(event_index>=0)deadline=(datetime)MathMin((long)deadline,Events[event_index]+3600);
 if(now<deadline)return;
 bool sent=trade.PositionClose(ticket);uint code=trade.ResultRetcode();
 MqlRates bar={};
 if(!sent || (code!=TRADE_RETCODE_DONE && code!=TRADE_RETCODE_DONE_PARTIAL)){
  updates++;if(code==TRADE_RETCODE_MARKET_CLOSED)closed_rejections++;
  if(now-last_rejected_close>=60){last_rejected_close=now;Log("time_close_rejected",bar);}
 }else Log("time_close",bar,0,0,0,0,0,"earliest executable quote at/after holding deadline");
}
void Enter(MqlRates &bar,MqlTick &quote,int direction,string signal){
 // The first observed trigger consumes the attempt even when its quote,
 // risk/target geometry, broker minimum, or execution is unacceptable.
 handled=true;
 request_bid=quote.bid;request_ask=quote.ask;
 double buffer=0.1*pre_atr+TickSize();
 double ep=direction>0?quote.ask:quote.bid;
 double sl=direction>0?Price(spike_low-buffer,-1):Price(spike_high+buffer,1);
 double distance=direction*(ep-sl);
 double tp=strategy_mode==0?Price(ep+direction*1.5*distance,direction):Price(fair);
 double reward=direction*(tp-ep);
 long age=(long)TimeCurrent()-(long)quote.time;
 if(age<0 || age>2 || quote.bid<=0 || quote.ask<quote.bid){Skip("trigger_quote_invalid_or_stale",bar);return;}
 if(positive_spread && quote.ask<=quote.bid){Skip("trigger_zero_spread_excluded",bar);return;}
 if(distance<=0 || reward<=0){Skip("nonpositive_stop_or_anchor_reward",bar);return;}
 if(quote.ask-quote.bid>0.1*distance){Skip("spread_above_ten_percent_stop",bar);return;}
 if(strategy_mode==1 && reward/distance<1.5-1e-9){
  Log("anchor_reward_below_1_5R",bar,sl,tp,0,0,0,"first midpoint cross consumed; no later attempt",reward/distance);filter_skips++;return;
 }
 double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((direction>0 && (sl>=quote.bid-min_distance || tp<=quote.bid+min_distance)) ||
    (direction<0 && (sl<=quote.ask+min_distance || tp>=quote.ask-min_distance))){
  Log("invalid_broker_stop_or_target",bar,sl,tp);filter_skips++;return;
 }
 double loss=0,budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100;
 if(budget<=0 || !OrderCalcProfit(direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1,ep,sl,loss) || loss>=0){
  failed++;Log("sizing_error",bar,sl,tp);return;
 }
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double max_lot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),min_lot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 double qty=NormalizeDouble(MathFloor(MathMin(budget/-loss,max_lot)/step+1e-9)*step,8);
 if(qty<min_lot){minimum_skips++;Log("minimum_lot_skip",bar,sl,tp,qty,budget,-loss);return;}
 if(quote.ask==quote.bid)zero_spread_entry_quotes++;
 bool sent=direction>0?trade.Buy(qty,_Symbol,0,sl,tp,"CPI raw continuation/fade"):trade.Sell(qty,_Symbol,0,sl,tp,"CPI raw continuation/fade");
 uint code=trade.ResultRetcode();bool ok=sent && (code==TRADE_RETCODE_DONE || code==TRADE_RETCODE_DONE_PARTIAL);
 if(!ok)failed++;
 Log(ok?"entry_"+signal:"entry_rejected",bar,sl,tp,qty,budget,-loss,"request-quote planned risk; delayed actual fill may differ",reward/distance);
}
void ConfirmImpulse(){
 datetime event=(datetime)Events[event_index],now=TimeCurrent();MqlRates bar[];
 if(now<event+60)return;
 if(CopyRates(_Symbol,PERIOD_M1,event,event+59,bar)!=1 || bar[0].time!=event){
  MqlRates empty={};Skip("missing_first_release_aligned_m1",empty);return;
 }
 have_impulse=true;first_close=bar[0].close;spike_high=bar[0].high;spike_low=bar[0].low;
 midpoint=(spike_high+spike_low)/2;previous_close=first_close;last_closed_bar=event;
 spike=first_close>fair?1:(first_close<fair?-1:0);
 double span=spike_high-spike_low;
 if(MathAbs(first_close-fair)<pre_atr || spike==0){Skip("weak_initial_impulse",bar[0]);return;}
 if(span<=0 || (spike>0 && (spike_high-first_close)/span>0.25) || (spike<0 && (first_close-spike_low)/span>0.25)){
  Skip("initial_close_not_in_outer_quartile",bar[0]);return;
 }
 Log("impulse_confirmed",bar[0],0,0,0,0,0,"release-aligned first M1 only; high/low/midpoint now frozen");
}
void Signal(MqlTick &quote){
 datetime event=(datetime)Events[event_index],now=TimeCurrent();MqlRates empty={};
 datetime deadline=event+(strategy_mode==0?300:600);
 if(now>=deadline){Skip("entry_window_expired",empty);return;}
 if(!have_impulse){ConfirmImpulse();if(!have_impulse || handled)return;}
 if(strategy_mode==0){
  // Signal thresholds use bid bars; the executable buy is at ask, sell at
  // bid. A gap is filled at the observed quote, never at the ideal level.
  bool crossed=spike>0?quote.bid>spike_high:quote.bid<spike_low;
  if(crossed){MqlRates first[];if(CopyRates(_Symbol,PERIOD_M1,event,event+59,first)==1)Enter(first[0],quote,spike,"continuation");}
  return;
 }
 MqlRates bar[];
 if(CopyRates(_Symbol,PERIOD_M1,1,1,bar)!=1){Skip("missing_completed_fade_bar",empty);return;}
 if(bar[0].time<=last_closed_bar)return;
 if(bar[0].time!=last_closed_bar+60 || bar[0].time+60>now){Skip("noncontiguous_fade_confirmation_bars",bar[0]);return;}
 bool crossed=spike>0?(previous_close>midpoint && bar[0].close<midpoint):(previous_close<midpoint && bar[0].close>midpoint);
 previous_close=bar[0].close;last_closed_bar=bar[0].time;
 if(!crossed)return;
 if(now-(bar[0].time+60)>2){Skip("fade_confirmation_quote_stale",bar[0]);return;}
 Enter(bar[0],quote,-spike,strategy_mode==1?"fade_min1_5R":"fade_anchor_diagnostic");
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0) || InpRiskPct<=0 || InpRiskPct>100)return INIT_PARAMETERS_INCORRECT;
 strategy_mode=(int)Cases[InpCase][0];positive_spread=(bool)Cases[InpCase][1];
 if(strategy_mode<0 || strategy_mode>2 || TickSize()<=0 || SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP)<=0)return INIT_PARAMETERS_INCORRECT;
 // Research metadata only; no signal or sizing rule is changed by this receipt.
 if(InpVerbose){
  int cf=FileOpen(Tag()+"-contract.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  if(cf==INVALID_HANDLE)return INIT_FAILED;
  FileWrite(cf,"symbol","point","tick_size","tick_value_loss","tick_value_profit","contract_size","volume_min","volume_step","volume_max","stops_level","currency_profit","currency_margin","digits");
  FileWrite(cf,_Symbol,_Point,TickSize(),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_PROFIT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_MARGIN),SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  FileClose(cf);
 }
 trade.SetExpertMagicNumber(MAGIC);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 if(InpVerbose){
  eqfile=FileOpen(Tag()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  qfile=FileOpen(Tag()+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  df=FileOpen(Tag()+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  if(eqfile==INVALID_HANDLE || qfile==INVALID_HANDLE || df==INVALID_HANDLE)return INIT_FAILED;
  FileWrite(eqfile,"epoch","balance","equity");
  FileWrite(qfile,"deal","position_id","epoch","entry","bid","ask","volume","spread_cash");
  FileWrite(df,"epoch","event_index","event_epoch","kind","reason","bar_epoch","open","high","low","close","fair","pre_atr","spike","first_news_close","pivot","pivot_epoch","pivot_confirm","sl","tp","lots","risk_budget","unit_loss","bid","ask","retcode","mode","require_positive_spread","impulse_high","impulse_low","impulse_midpoint","pre_quote_epoch","pre_quote_bid","pre_quote_ask","info","entry_rr","request_bid","request_ask");
 }
 return INIT_SUCCEEDED;
}
void OnTick(){
 ticks++;MqlTick quote={};if(!SymbolInfoTick(_Symbol,quote))return;
 datetime now=TimeCurrent();Manage();ulong ticket;
 if(active && now>=Events[event_index]+3600 && !OurPosition(ticket)){
  MqlRates empty={};Log(handled?"event_end":"no_signal",empty);active=false;
 }
 if(!active){
  while(next_event<ArraySize(Events) && now>=Events[next_event]+3600){
   event_index=next_event;MqlRates empty={};Log("no_tradable_event_window",empty);next_event++;
  }
  if(next_event<ArraySize(Events) && now>=Events[next_event] && now<Events[next_event]+3600)StartEvent(next_event++,quote);
 }
 Snapshot();
 if(active && !handled && !OurPosition(ticket))Signal(quote);
 previous_quote=quote;have_previous_quote=true;
}
double OnTester(){
 HistorySelect(0,TimeCurrent());int out=FileOpen(Tag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 if(out==INVALID_HANDLE)return -1e99;
 FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=MAGIC)continue;
  ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
  FileWrite(out,deal,HistoryDealGetInteger(deal,DEAL_POSITION_ID),(long)HistoryDealGetInteger(deal,DEAL_TIME),HistoryDealGetInteger(deal,DEAL_ENTRY),HistoryDealGetInteger(deal,DEAL_TYPE),HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP));
 }
 FileClose(out);out=FileOpen(Tag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
 ulong ticket;
 FileWrite(out,"net","equity_dd","balance_dd","failed_entries","failed_updates","market_closed_updates","balance","open_position","last_quote_epoch","ticks","mt5_sharpe","trades","minimum_lot_skips","filter_skips","events_seen","zero_spread_entry_quotes");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),failed,updates,closed_rejections,AccountInfoDouble(ACCOUNT_BALANCE),(int)OurPosition(ticket),(long)TimeCurrent(),ticks,TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_TRADES),minimum_skips,filter_skips,events_seen,zero_spread_entry_quotes);
 FileClose(out);Snapshot(true);if(eqfile!=INVALID_HANDLE)FileFlush(eqfile);
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(qfile==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal) || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=MAGIC)return;
 MqlTick quote={};if(!SymbolInfoTick(_Symbol,quote))return;
 double qty=HistoryDealGetDouble(trans.deal,DEAL_VOLUME),cash=0;
 ENUM_ORDER_TYPE kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE)==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 bool ok=OrderCalcProfit(kind,_Symbol,qty,quote.bid,quote.ask,cash);
 FileWrite(qfile,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),HistoryDealGetInteger(trans.deal,DEAL_ENTRY),quote.bid,quote.ask,qty,ok?MathAbs(cash):-1);
}
void OnDeinit(const int reason){
 if(eqfile!=INVALID_HANDLE)FileClose(eqfile);
 if(qfile!=INVALID_HANDLE)FileClose(qfile);
 if(df!=INVALID_HANDLE)FileClose(df);
}

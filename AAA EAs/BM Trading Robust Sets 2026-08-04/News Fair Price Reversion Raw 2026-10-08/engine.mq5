#property strict
#property description "TESTER ONLY: raw CPI/NFP/FOMC reversion to pre-release price"
#include <Trade/Trade.mqh>
input int InpCase=0;
input string InpTag="news-fair-price";
input bool InpVerbose=false;
input double InpRiskPct=1.0;
const int MAGIC=26100881;
CTrade trade;
int atr_handle=INVALID_HANDLE,eqfile=INVALID_HANDLE,qfile=INVALID_HANDLE,df=INVALID_HANDLE;
int next_event=0,event_index=-1,spike=0,failed=0,updates=0,closed_rejections=0,minimum_skips=0,filter_skips=0,events_seen=0;
long ticks=0,minute=-1;
datetime last_bar=0,pivot_epoch=0,pivot_confirm=0,last_rejected_close=0;
bool active=false,handled=false,have_impulse=false,allow_longs=false;
double fair=0,pre_atr=0,pivot=0,previous_close=0,first_close=0;
string Tag(){return InpTag+"-"+(string)InpCase;}
double Price(double value){double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(value/step)*step,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
bool OurPosition(ulong &ticket){ticket=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC){ticket=t;return true;}}return false;}
void Log(string reason,MqlRates &bar,double sl=0,double tp=0,double qty=0,double budget=0,double unit_loss=0){
 if(df==INVALID_HANDLE)return;
 MqlTick q={};SymbolInfoTick(_Symbol,q);
 FileWrite(df,(long)TimeCurrent(),event_index,event_index>=0?Events[event_index]:0,event_index>=0?Kinds[event_index]:"",reason,
  (long)bar.time,bar.open,bar.high,bar.low,bar.close,fair,pre_atr,spike,first_close,pivot,(long)pivot_epoch,(long)pivot_confirm,
  sl,tp,qty,budget,unit_loss,q.bid,q.ask,trade.ResultRetcode());
}
void Snapshot(){
 ticks++;datetime now=TimeCurrent();
 if(eqfile!=INVALID_HANDLE && now/60!=minute){minute=now/60;FileWrite(eqfile,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
}
void StartEvent(int index){
 event_index=index;active=true;handled=false;have_impulse=false;spike=0;fair=0;pre_atr=0;pivot=0;pivot_epoch=0;pivot_confirm=0;previous_close=0;first_close=0;events_seen++;
 MqlRates before[];datetime event=(datetime)Events[index];
 if(CopyRates(_Symbol,PERIOD_M1,event-60,event-1,before)!=1 || before[0].time!=event-60){
  MqlRates dummy={};handled=true;Log("missing_exact_pre_news_bar",dummy);filter_skips++;return;
 }
 fair=Price(before[0].close);
 int shift=iBarShift(_Symbol,PERIOD_M5,event-300,true);double values[];
 if(shift<0 || CopyBuffer(atr_handle,0,shift,1,values)!=1 || values[0]<=0){handled=true;Log("pre_news_atr_unavailable",before[0]);filter_skips++;return;}
 pre_atr=values[0];Log("event_start",before[0]);
}
void Manage(){
 ulong ticket;if(!OurPosition(ticket))return;
 datetime filled=(datetime)PositionGetInteger(POSITION_TIME),now=TimeCurrent();
 datetime deadline=filled+3600;
 if(event_index>=0)deadline=(datetime)MathMin((long)deadline,Events[event_index]+5400);
 if(now<deadline)return;
 bool sent=trade.PositionClose(ticket);uint code=trade.ResultRetcode();
 if(!sent || (code!=TRADE_RETCODE_DONE && code!=TRADE_RETCODE_DONE_PARTIAL)){
  updates++;if(code==TRADE_RETCODE_MARKET_CLOSED)closed_rejections++;
  if(now-last_rejected_close>=60){last_rejected_close=now;MqlRates b[];if(CopyRates(_Symbol,PERIOD_M1,1,1,b)==1)Log("time_close_rejected",b[0]);}
 }else{MqlRates b[];if(CopyRates(_Symbol,PERIOD_M1,1,1,b)==1)Log("time_close",b[0]);}
}
void Enter(MqlRates &bar,string signal){
 int dir=-spike;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double ep=dir>0?q.ask:q.bid,sl=Price(ep+(dir>0?-1:1)*2*pre_atr),tp=fair;
 double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 handled=true;
 if((dir>0 && (sl>=q.bid-min_distance || tp<=q.bid+min_distance)) || (dir<0 && (sl<=q.ask+min_distance || tp>=q.ask-min_distance))){filter_skips++;Log("invalid_broker_stop_or_target",bar,sl,tp);return;}
 double loss=0,budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100;
 if(!OrderCalcProfit(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1,ep,sl,loss) || loss>=0){failed++;Log("sizing_error",bar,sl,tp);return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),qty=NormalizeDouble(MathFloor(budget/-loss/step+1e-9)*step,8);
 qty=MathMin(qty,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(qty<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){minimum_skips++;Log("minimum_lot_skip",bar,sl,tp,qty,budget,-loss);return;}
 bool sent=dir>0?trade.Buy(qty,_Symbol,0,sl,tp,"Raw news fair-price reversion"):trade.Sell(qty,_Symbol,0,sl,tp,"Raw news fair-price reversion");
 uint code=trade.ResultRetcode();bool ok=sent && (code==TRADE_RETCODE_DONE || code==TRADE_RETCODE_DONE_PARTIAL);
 if(!ok)failed++;
 Log(ok?"entry_"+signal:"entry_rejected",bar,sl,tp,qty,budget,-loss);
}
void Signal(MqlRates &b){
 datetime event=(datetime)Events[event_index],now=TimeCurrent();
 if(b.time<event || b.time+60>now)return;
 if(now>=event+1800){handled=true;Log("entry_window_expired",b);return;}
 if(!have_impulse){
  have_impulse=true;first_close=b.close;
  if(b.time!=event){handled=true;filter_skips++;Log("missing_first_news_candle",b);return;}
  spike=b.close>=fair+pre_atr?1:(b.close<=fair-pre_atr?-1:0);
  previous_close=b.close;
  if(spike==0){handled=true;filter_skips++;Log("weak_initial_impulse",b);return;}
  if(spike<0 && !allow_longs){handled=true;Log("down_spike_not_short_setup",b);return;}
  Log("impulse_confirmed",b);return;
 }
 // Never sell below the pre-news target or buy above it after a reversion.
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 if((spike>0 && q.bid<=fair) || (spike<0 && q.ask>=fair)){handled=true;Log("fair_price_reached_before_entry",b);return;}
 double range=b.high-b.low,body=MathAbs(b.close-b.open);
 bool displacement=range>0 && body>=.5*pre_atr && body/range>=.6 &&
  (spike>0?(b.close<b.open && (b.close-b.low)/range<=.25):(b.close>b.open && (b.high-b.close)/range<=.25));
 bool structure=pivot>0 && pivot_confirm<=b.time &&
  (spike>0?(previous_close>=pivot && b.close<pivot):(previous_close<=pivot && b.close>pivot));
 if(displacement || structure){Enter(b,displacement?"displacement":"structure");return;}
 // A three-bar pivot exists only after its right-hand M1 candle closes.
 // Test the previously confirmed pivot first; no future candle is accessed.
 MqlRates bars[];
 if(CopyRates(_Symbol,PERIOD_M1,1,3,bars)==3 && bars[1].time>=event && bars[2].time==b.time && bars[0].time+60==bars[1].time && bars[1].time+60==bars[2].time){
  bool found=spike>0?(bars[1].low<bars[0].low && bars[1].low<bars[2].low):(bars[1].high>bars[0].high && bars[1].high>bars[2].high);
  if(found){pivot=spike>0?bars[1].low:bars[1].high;pivot_epoch=bars[1].time;pivot_confirm=b.time+60;Log("pivot_confirmed",b);}
 }
 previous_close=b.close;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0))return INIT_PARAMETERS_INCORRECT;
 allow_longs=(bool)Cases[InpCase][0];atr_handle=iATR(_Symbol,PERIOD_M5,14);if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(MAGIC);trade.SetTypeFillingBySymbol(_Symbol);
 if(InpVerbose){
  eqfile=FileOpen(Tag()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');qfile=FileOpen(Tag()+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');df=FileOpen(Tag()+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
  if(eqfile==INVALID_HANDLE || qfile==INVALID_HANDLE || df==INVALID_HANDLE)return INIT_FAILED;
  FileWrite(eqfile,"epoch","balance","equity");FileWrite(qfile,"deal","position_id","epoch","entry","bid","ask","volume","spread_cash");
  FileWrite(df,"epoch","event_index","event_epoch","kind","reason","bar_epoch","open","high","low","close","fair","pre_atr","spike","first_news_close","pivot","pivot_epoch","pivot_confirm","sl","tp","lots","risk_budget","unit_loss","bid","ask","retcode");
 }
 return INIT_SUCCEEDED;
}
void OnTick(){
 Snapshot();Manage();datetime now=TimeCurrent();ulong ticket;
 if(active && now>=Events[event_index]+5400 && !OurPosition(ticket)){MqlRates empty={};Log(handled?"event_end":"no_signal",empty);active=false;}
 if(!active){
  while(next_event<ArraySize(Events) && now>=Events[next_event]+5400){event_index=next_event;MqlRates empty={};Log("no_tradable_event_window",empty);next_event++;}
  if(next_event<ArraySize(Events) && now>=Events[next_event] && now<Events[next_event]+5400)StartEvent(next_event++);
 }
 if(!active || handled || OurPosition(ticket))return;
 MqlRates bars[];if(CopyRates(_Symbol,PERIOD_M1,1,1,bars)!=1 || bars[0].time==last_bar)return;
 last_bar=bars[0].time;Signal(bars[0]);
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
 FileWrite(out,"net","equity_dd","balance_dd","failed_entries","failed_updates","market_closed_updates","balance","open_position","last_quote_epoch","ticks","mt5_sharpe","trades","minimum_lot_skips","filter_skips","events_seen");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),failed,updates,closed_rejections,AccountInfoDouble(ACCOUNT_BALANCE),(int)OurPosition(t),(long)TimeCurrent(),ticks,TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_TRADES),minimum_skips,filter_skips,events_seen);FileClose(out);
 if(eqfile!=INVALID_HANDLE){FileWrite(eqfile,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileFlush(eqfile);}
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(qfile==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal) || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=MAGIC)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double qty=HistoryDealGetDouble(trans.deal,DEAL_VOLUME),cash=0;ENUM_ORDER_TYPE kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE)==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 bool ok=OrderCalcProfit(kind,_Symbol,qty,q.bid,q.ask,cash);
 FileWrite(qfile,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),HistoryDealGetInteger(trans.deal,DEAL_ENTRY),q.bid,q.ask,qty,ok?MathAbs(cash):-1);
}
void OnDeinit(const int reason){if(eqfile!=INVALID_HANDLE)FileClose(eqfile);if(qfile!=INVALID_HANDLE)FileClose(qfile);if(df!=INVALID_HANDLE)FileClose(df);if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);}

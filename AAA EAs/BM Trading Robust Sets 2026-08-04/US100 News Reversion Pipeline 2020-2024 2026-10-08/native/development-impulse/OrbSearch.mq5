double Cases[][9]={{1,4,0.5,0.5,0.6,0,30,60,1},{1,4,1,0.5,0.6,0,30,60,1},{1,4,1.5,0.5,0.6,0,30,60,1},{1,4,2,0.5,0.6,0,30,60,1},{1,2.5,0.5,0.5,0.6,0,30,60,1},{1,2.5,1,0.5,0.6,0,30,60,1},{1,2.5,1.5,0.5,0.6,0,30,60,1},{1,2.5,2,0.5,0.6,0,30,60,1}};
long Events[]={1578663000,1579008600,1580324400,1581082200,1581600600,1583501400,1583929800,1585917000,1586521800,1588183200,1588941000,1589286600,1591360200,1591792200,1591812000,1593693000,1594729800,1596045600,1596803400,1597235400,1599222600,1599827400,1600279200,1601641800,1602592200,1604602800,1604669400,1605187800,1607088600,1607607000,1608145200,1610112600,1610544600,1611774000,1612531800,1612963800,1614951000,1615383000,1616004000,1617366600,1618317000,1619632800,1620390600,1620822600,1622809800,1623328200,1623866400,1625229000,1626179400,1627495200,1628253000,1628685000,1630672200,1631622600,1632333600,1633696200,1634128200,1635962400,1636115400,1636551000,1638538200,1639143000,1639594800,1641562200,1641994200,1643223600,1643981400,1644499800,1646400600,1646919000,1647453600,1648816200,1649766600,1651687200,1651840200,1652272200,1654259400,1654864200,1655316000,1657283400,1657715400,1658944800,1659702600,1660134600,1662121800,1663072200,1663783200,1665145800,1665664200,1667412000,1667565000,1668087000,1669987800,1670938200,1671044400,1673011800,1673530200,1675278000,1675431000,1676381400,1678455000,1678797000,1679508000,1680870600,1681302600,1683136800,1683289800,1683721800,1685709000,1686659400,1686765600,1688733000,1689165000,1690394400,1691152200,1691670600,1693571400,1694608200,1695232800,1696595400,1697113800,1698861600,1699014600,1699968600,1702042200,1702387800,1702494000,1704461400,1704979800,1706727600,1706880600,1707831000,1709904600,1710246600,1710957600,1712320200,1712752200,1714586400,1714739400,1715776200,1717763400,1718195400,1718215200,1720182600,1720701000,1722448800,1722601800,1723638600,1725625800,1726057800,1726682400,1728045000,1728563400,1730464200,1731006000,1731504600,1733491800,1733923800,1734548400,1736515800,1736947800,1738177200,1738935000,1739367000,1741354200,1741782600,1742407200,1743769800,1744288200,1746189000,1746640800,1747139400,1749213000,1749645000,1750269600,1751545800,1752582600,1753898400,1754051400,1755001800,1757075400,1757593800,1758132000,1761309000,1761760800,1763645400,1765393200,1765891800,1766064600,1767965400,1768311000,1769626800,1770816600,1770989400,1772803800,1773232200,1773856800,1775219400,1775824200,1777485600,1778243400,1778589000,1780662600,1781094600,1781719200,1782995400,1784032200,1785348000,1786105800,1786537800,1788525000,1789129800,1789581600,1790944200};
string Kinds[]={"NFP","CPI","FOMC","NFP","CPI","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","NFP","FOMC","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","NFP","FOMC","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","CPI","FOMC","NFP","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP","CPI","FOMC","NFP","CPI","NFP","CPI","FOMC","NFP"};
#property strict
#property description "TESTER ONLY: research CPI/NFP/FOMC reversion to pre-release price"
#include <Trade/Trade.mqh>
input int InpCase=0;
input string InpTag="news-reversion-pipeline";
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
double sl_mult=2,impulse_mult=1,body_mult=.5,body_fraction=.6,target_fraction=1;
int signal_mode=0,window_minutes=30,hold_minutes=60;
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
 datetime deadline=filled+hold_minutes*60;
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
 double ep=dir>0?q.ask:q.bid,sl=Price(ep+(dir>0?-1:1)*sl_mult*pre_atr),tp=Price(ep+(fair-ep)*target_fraction);
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
 if(now>=event+window_minutes*60){handled=true;Log("entry_window_expired",b);return;}
 if(!have_impulse){
  have_impulse=true;first_close=b.close;
  if(b.time!=event){handled=true;filter_skips++;Log("missing_first_news_candle",b);return;}
  spike=b.close>=fair+impulse_mult*pre_atr?1:(b.close<=fair-impulse_mult*pre_atr?-1:0);
  previous_close=b.close;
  if(spike==0){handled=true;filter_skips++;Log("weak_initial_impulse",b);return;}
  if(spike<0 && !allow_longs){handled=true;Log("down_spike_not_short_setup",b);return;}
  Log("impulse_confirmed",b);return;
 }
 // Never sell below the pre-news target or buy above it after a reversion.
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 if((spike>0 && q.bid<=fair) || (spike<0 && q.ask>=fair)){handled=true;Log("fair_price_reached_before_entry",b);return;}
 double range=b.high-b.low,body=MathAbs(b.close-b.open);
 bool displacement=range>0 && body>=body_mult*pre_atr && body/range>=body_fraction &&
  (spike>0?(b.close<b.open && (b.close-b.low)/range<=.25):(b.close>b.open && (b.high-b.close)/range<=.25));
 bool structure=pivot>0 && pivot_confirm<=b.time &&
  (spike>0?(previous_close>=pivot && b.close<pivot):(previous_close<=pivot && b.close>pivot));
 if((signal_mode!=2 && displacement) || (signal_mode!=1 && structure)){Enter(b,signal_mode!=2 && displacement?"displacement":"structure");return;}
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
 allow_longs=(bool)Cases[InpCase][0];sl_mult=Cases[InpCase][1];impulse_mult=Cases[InpCase][2];body_mult=Cases[InpCase][3];body_fraction=Cases[InpCase][4];signal_mode=(int)Cases[InpCase][5];window_minutes=(int)Cases[InpCase][6];hold_minutes=(int)Cases[InpCase][7];target_fraction=Cases[InpCase][8];atr_handle=iATR(_Symbol,PERIOD_M5,14);if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
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

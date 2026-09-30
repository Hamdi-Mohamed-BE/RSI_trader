#property strict
#property version "1.00"
#property description "Tester-only gold clock bias; no live initialization allowed"
#include <Trade/Trade.mqh>
input bool InpControl=false;
input double InpLots=0.10;
input int InpEntryMinute=1380;
input int InpHoldMinutes=120;
input datetime InpTradeFrom=D'2021.09.27';
input string InpTag="smoke";
input long InpMagic=9292300;
CTrade trade;
datetime lastMinute=0,tradedDay=0,lastClose=0,opened=0;
int entries=0,entryFails=0,closeFails=0,skips=0,trace=INVALID_HANDLE;
double base=0;bool tracking=false;
datetime Make(int y,int m,int day,int h){MqlDateTime d={};d.year=y;d.mon=m;d.day=day;d.hour=h;return StructToTime(d);}
int LastSunday(int y,int m){MqlDateTime d;datetime t=Make(y,m+1,1,0)-86400;TimeToStruct(t,d);return d.day-d.day_of_week;}
datetime London(datetime t){MqlDateTime d;TimeToStruct(t,d);return t+((t>=Make(d.year,3,LastSunday(d.year,3),1)&&t<Make(d.year,10,LastSunday(d.year,10),1))?3600:0);}
datetime NY(datetime t){MqlDateTime d,a;TimeToStruct(t,d);TimeToStruct(Make(d.year,3,1,0),a);int march=1+(7-a.day_of_week)%7+7;TimeToStruct(Make(d.year,11,1,0),a);int nov=1+(7-a.day_of_week)%7;return t-((t>=Make(d.year,3,march,7)&&t<Make(d.year,11,nov,6))?4:5)*3600;}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}return false;}
bool RollCross(datetime t,int minutes){datetime x=NY(t),y=NY(t+minutes*60);datetime boundary=x-x%86400+17*3600;if(boundary<=x)boundary+=86400;return y>=boundary;}
void Close(){ulong ticket;if(!Own(ticket))return;datetime now=TimeCurrent();if(now-lastClose<60)return;lastClose=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("GC_CLOSE_FAIL %u",trade.ResultRetcode());}}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;if(_Symbol!="XAUUSD"||InpLots<=0||InpHoldMinutes<1)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 FolderCreate("CalyxGoldClock20260929",FILE_COMMON);trace=FileOpen("CalyxGoldClock20260929\\"+InpTag+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(trace,"time","balance","equity");
 PrintFormat("GC_SPEC symbol=%s broker=%s currency=%s contract=%.8f min=%.8f step=%.8f tick=%.8f",_Symbol,AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_CURRENCY),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));return INIT_SUCCEEDED;}
void OnTick(){datetime now=TimeCurrent();ulong ticket;bool own=Own(ticket);
 if(own){datetime openedAt=(datetime)PositionGetInteger(POSITION_TIME);MqlDateTime d;TimeToStruct(now,d);
  if(now-openedAt>=InpHoldMinutes*60 || (d.day_of_week==5 && now%86400>=20*3600+45*60) || (NY(now)%86400>=16*3600+59*60 && NY(now)%86400<17*3600))Close();}
 datetime minute=now-now%60;if(minute==lastMinute)return;lastMinute=minute;
 if(now>=InpTradeFrom)FileWrite(trace,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),8),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),8));
 if(now<InpTradeFrom)return;
 datetime local=InpControl?now:London(now),day=local-local%86400;MqlDateTime dt;TimeToStruct(local,dt);if(dt.day_of_week==0||dt.day_of_week==6||tradedDay==day)return;
 int anchor=InpControl?(int)((((long)(day/86400)*1103515245+290929)%2147483647)%48)*30:InpEntryMinute;
 int seconds=(int)(local%86400)-anchor*60;if(seconds<0||seconds>=300)return;
 tradedDay=day;if(Own(ticket)||RollCross(now,InpHoldMinutes)){skips++;return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0){skips++;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),volume=MathCeil((InpLots-1e-12)/step)*step,margin=0;
 if(!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,volume,q.ask,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 if(trade.Buy(volume,_Symbol,0,0,0,"GoldClock") && trade.ResultRetcode()==TRADE_RETCODE_DONE){entries++;PrintFormat("GC_ENTRY utc=%I64d local=%I64d quote=%.8f fill=%.8f spread=%.8f volume=%.8f",(long)now,(long)local,q.ask,trade.ResultPrice(),q.ask-q.bid,volume);}
 else{entryFails++;PrintFormat("GC_ENTRY_FAIL %u",trade.ResultRetcode());}
}
struct Item{ulong id;datetime opened,closed;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){HistorySelect(0,TimeCurrent());Item rows[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen("CalyxGoldClock20260929\\"+InpTag+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","open_epoch","close_epoch","volume","closed_volume","open_price","close_price","gross_profit","commission","swap","fee","net_profit");
 for(int k=0;k<n;k++){double net=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;FileWrite(f,rows[k].id,(long)rows[k].opened,(long)rows[k].closed,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,net);}
 FileClose(f);return TesterStatistics(STAT_PROFIT_FACTOR);}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);PrintFormat("GC_SUMMARY entries=%d entryFails=%d closeFails=%d skips=%d",entries,entryFails,closeFails,skips);}

#include "Extensions.mqh"
#include "Engine.mqh"
struct Initial{ulong id;double sl,tp,risk,budget;};
Initial initial[];
int trace=INVALID_HANDLE,maxOpen=0;datetime traceBar=0;
double auditRequested=0;
string Dir="GoldTargets20261002\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
string Module(){return Cases[InpCase][0]==1?"T_PROGRESS":"S_SLOW";}
void Capture(){int count=0;
 for(int j=0;j<PositionsTotal();j++){ulong ticket=PositionGetTicket(j);if(ticket==0||PositionGetString(POSITION_SYMBOL)!=_Symbol||(long)PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic)continue;
  count++;ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);bool found=false;for(int k=0;k<ArraySize(initial);k++)if(initial[k].id==id){found=true;break;}if(found)continue;
  int n=ArraySize(initial);ArrayResize(initial,n+1);initial[n].id=id;initial[n].sl=PositionGetDouble(POSITION_SL);initial[n].tp=PositionGetDouble(POSITION_TP);initial[n].budget=auditRequested;
  double loss=0;ENUM_ORDER_TYPE type=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
  if(OrderCalcProfit(type,_Symbol,PositionGetDouble(POSITION_VOLUME),PositionGetDouble(POSITION_PRICE_OPEN),initial[n].sl,loss))initial[n].risk=MathAbs(loss);
 }maxOpen=MathMax(maxOpen,count);
}
void Trace(){if(trace==INVALID_HANDLE||TimeCurrent()<InpTradeFrom)return;datetime t=TimeCurrent(),bar=t-t%300;if(bar==traceBar)return;traceBar=bar;FileWrite(trace,(long)t,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),PositionsTotal());}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)||_Period!=PERIOD_H4||InpCase<0||InpCase>=ArrayRange(Cases,0)||InpCase2>=0||InpCase3>=0||InpControl||InpRiskPercent!=1)return INIT_FAILED;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 InpRewardRisk=Cases[InpCase][6];int result=OriginalOnInit();if(result!=INIT_SUCCEEDED)return result;
 FolderCreate("GoldTargets20261002",FILE_COMMON);
 if(!MQLInfoInteger(MQL_OPTIMIZATION)){trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(trace==INVALID_HANDLE)return INIT_FAILED;FileWrite(trace,"epoch","balance","equity","margin","positions");}
 return INIT_SUCCEEDED;
}
void OnTick(){if(TimeCurrent()<InpTradeFrom)return;auditRequested=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;OriginalOnTick();Capture();Trace();}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);OriginalOnDeinit(reason);}
struct Item{ulong id;long magic;datetime opened,closed;int side,reason;bool boundary;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){HistorySelect(0,TimeCurrent());Item rows[];int n=0,boundary=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;rows[k].magic=HistoryDealGetInteger(deal,DEAL_MAGIC);}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;rows[k].reason=(int)HistoryDealGetInteger(deal,DEAL_REASON);if(StringFind(HistoryDealGetString(deal,DEAL_COMMENT),"end of test")>=0){boundary++;rows[k].boundary=true;}}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen(Dir+Tag()+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","module","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit","exit_reason","test_end");
 double gp=0,gl=0,net=0;int wins=0,bad=0,tps=0,smallSlWins=0;
 for(int k=0;k<n;k++){int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double p=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;net+=p;if(p>0){gp+=p;wins++;}else gl-=p;
  double sl=ix>=0?initial[ix].sl:0,tp=ix>=0?initial[ix].tp:0,risk=ix>=0?initial[ix].risk:0,budget=ix>=0?initial[ix].budget:0;if(risk<=0||budget<=0)bad++;
  if(rows[k].reason==DEAL_REASON_TP)tps++;if(rows[k].reason==DEAL_REASON_SL&&p>0)smallSlWins++;
  FileWrite(f,rows[k].id,Module(),(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,sl,tp,budget,risk,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p,rows[k].reason,(int)rows[k].boundary);
 }
 FileClose(f);double pf=gl>0?gp/gl:(gp>0?99:0),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
 f=FileOpen(Dir+Tag()+"-net.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 FileWriteString(f,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"balance_dd_pct\":%.8f,\"entry_fail\":%d,\"close_fail\":%d,\"modify_fail\":%d,\"cancel_fail\":0,\"bad_risk\":%d,\"boundary\":%d,\"max_open\":%d,\"full_tp\":%d,\"positive_sl_exits\":%d,\"no_changes\":%d}",n,net,pf,n>0?100.0*wins/n:0,dd,TesterStatistics(STAT_BALANCE_DDREL_PERCENT),entryFails,closeFails,modifyFails,bad,boundary,maxOpen,tps,smallSlWins,noChanges));FileClose(f);
 return n>0?(pf-1)*MathSqrt(n)/(1+dd/10):-1;
}

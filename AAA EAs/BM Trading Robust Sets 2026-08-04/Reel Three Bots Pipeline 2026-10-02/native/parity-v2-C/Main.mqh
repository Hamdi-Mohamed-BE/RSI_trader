#include <Trade/Trade.mqh>
input int InpCase=0;
input int InpCase2=-1;
input int InpCase3=-1;
input bool InpControl=false;
input bool InpRetryClosed=false;
input double InpRiskPercent=1.0;
input double InpFixedRiskUSD=100.0;
input uint InpSeed=301;
input datetime InpTradeFrom=D'2021.10.01';
input string InpTag="smoke";
input long InpMagic=9801000;
bool Control;uint Seed;
#include "Engine.mqh"
RRModule S[3];int NS=0,trace=INVALID_HANDLE,maxOpen=0;
datetime traceBar=0;long lastStamp[3];double lastBid[3],lastAsk[3];
string Dir="ReelPipeline20261002\\";
string Tag(){return InpTag+"-"+(string)InpCase;}
string Name(int slot){return S[slot].BOT==1?"A_RANGE":(S[slot].BOT==2?"B_ATR":"C_DON");}
void Process(int s){S[s].InpFixedRiskUSD=InpRiskPercent>0?AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100:InpFixedRiskUSD;S[s].OnTick();}
void Secondary(int s){MqlTick q;if(!SymbolInfoTick(S[s].m_symbol,q)||q.time>TimeCurrent())return;if(q.time_msc!=lastStamp[s]||q.bid!=lastBid[s]||q.ask!=lastAsk[s]){lastStamp[s]=q.time_msc;lastBid[s]=q.bid;lastAsk[s]=q.ask;Process(s);}}
void Trace(){if(trace==INVALID_HANDLE||TimeCurrent()<InpTradeFrom)return;datetime t=TimeCurrent(),bar=t-t%300;if(bar==traceBar)return;traceBar=bar;int n=0;for(int s=0;s<NS;s++)n+=S[s].PositionCount();maxOpen=MathMax(maxOpen,n);FileWrite(trace,(long)t,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),n);}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;Control=InpControl;Seed=InpSeed;
 int n=ArrayRange(Cases,0);if(InpCase<0||InpCase>=n||InpCase2>=n||InpCase3>=n||InpRiskPercent<0||InpRiskPercent>1)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 int list[3];list[0]=InpCase;list[1]=InpCase2;list[2]=InpCase3;
 for(int j=0;j<3;j++){if(list[j]<0)continue;int k=list[j],kind=(int)Cases[k][0]+1;string symbol=kind==1?"DE30":"XAUUSD";if(!SymbolSelect(symbol,true))return INIT_FAILED;
  S[NS].Configure(kind,symbol,InpFixedRiskUSD,InpMagic+NS,InpTradeFrom,0,true,true,1000);S[NS].Features(k);if(S[NS].Init()!=INIT_SUCCEEDED)return INIT_FAILED;lastStamp[NS]=-1;lastBid[NS]=lastAsk[NS]=0;NS++;}
 FolderCreate("ReelPipeline20261002",FILE_COMMON);
 if(!MQLInfoInteger(MQL_OPTIMIZATION)){trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(trace==INVALID_HANDLE)return INIT_FAILED;FileWrite(trace,"epoch","balance","equity","margin","positions");}
 if(NS>1)EventSetTimer(1);return INIT_SUCCEEDED;
}
void OnTick(){for(int s=0;s<NS;s++){if(S[s].m_symbol==_Symbol)Process(s);else Secondary(s);}int count=0;for(int s=0;s<NS;s++)count+=S[s].PositionCount();maxOpen=MathMax(maxOpen,count);Trace();}
void OnTimer(){for(int s=0;s<NS;s++)if(S[s].m_symbol!=_Symbol)Secondary(s);Trace();}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &rq,const MqlTradeResult &res){for(int s=0;s<NS;s++){
 S[s].OnTradeTransaction(tx,rq,res);
 if(tx.type==TRADE_TRANSACTION_DEAL_ADD&&HistoryDealSelect(tx.deal)&&HistoryDealGetInteger(tx.deal,DEAL_MAGIC)==S[s].InpMagic&&HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_OUT&&HistoryDealGetInteger(tx.deal,DEAL_REASON)==DEAL_REASON_SL&&S[s].P(26)>0){S[s].buyArmed=S[s].sellArmed=true;}
}}
struct Item{ulong id;long magic;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){HistorySelect(0,TimeCurrent());Item rows[];int n=0,boundary=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
 ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
 double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
 if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;rows[k].magic=HistoryDealGetInteger(deal,DEAL_MAGIC);}
 else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;if(StringFind(HistoryDealGetString(deal,DEAL_COMMENT),"end of test")>=0)boundary++;}
 rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);}
 int f=FileOpen(Dir+Tag()+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","module","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 double gp=0,gl=0,net=0;int wins=0,bad=0;
 for(int k=0;k<n;k++){int slot=(int)(rows[k].magic-InpMagic),ix=-1;if(slot>=0&&slot<NS)for(int z=0;z<ArraySize(S[slot].initial);z++)if(S[slot].initial[z].id==rows[k].id){ix=z;break;}
 double p=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;net+=p;if(p>0){gp+=p;wins++;}else gl-=p;
 double sl=ix>=0?S[slot].initial[ix].sl:0,tp=ix>=0?S[slot].initial[ix].tp:0,risk=ix>=0?S[slot].initial[ix].risk:0,budget=ix>=0?S[slot].initial[ix].budget:0;if(risk<=0||budget<=0)bad++;
 FileWrite(f,rows[k].id,slot>=0&&slot<NS?Name(slot):"?",(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,sl,tp,budget,risk,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p);}
 FileClose(f);double pf=gl>0?gp/gl:(gp>0?99:0),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);int ef=0,cf=0,mf=0,cc=0,ps=0,cs=0,ds=0,ca=0,pa=0,pas=0,tr=0;
 for(int s=0;s<NS;s++){ef+=S[s].entryFails;cf+=S[s].closeFails;mf+=S[s].modifyFails;ps+=S[s].priceSkips;cs+=S[s].closedSkips;ds+=S[s].dataSkips;ca+=S[s].cancelFails;pa+=S[s].partialCount;pas+=S[s].partialSkips;tr+=S[s].trailCount;}
 f=FileOpen(Dir+Tag()+"-net.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 FileWriteString(f,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"balance_dd_pct\":%.8f,\"entry_fail\":%d,\"close_fail\":%d,\"close_closed\":%d,\"modify_fail\":%d,\"modify_closed\":%d,\"cancel_fail\":%d,\"bad_risk\":%d,\"boundary\":%d,\"partials\":%d,\"partial_skips\":%d,\"constraint_skips\":%d,\"stale\":%d,\"retries\":0,\"trails\":%d,\"max_open\":%d}",n,net,pf,n>0?100.0*wins/n:0,dd,TesterStatistics(STAT_BALANCE_DDREL_PERCENT),ef,cf,cs,mf,cc,ca,bad,boundary,pa,pas,ps,ds,tr,maxOpen));FileClose(f);
 return n>0&&net>0?(pf-1)*MathSqrt(n)/(1+dd/10):-1;
}
void OnDeinit(const int why){EventKillTimer();if(trace!=INVALID_HANDLE)FileClose(trace);for(int s=0;s<NS;s++)S[s].OnDeinit(why);}

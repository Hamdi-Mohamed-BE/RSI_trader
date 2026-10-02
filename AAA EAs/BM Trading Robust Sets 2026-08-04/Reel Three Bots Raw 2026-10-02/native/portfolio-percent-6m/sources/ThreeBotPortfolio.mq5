#property strict
#property version "1.00"
#property description "Tester-only three-module shared USD hedging portfolio"
#include "PortfolioModules.mqh"
input double InpFixedRiskUSD=100.0;
input double InpRiskPercent=1.0; // current shared balance; 0 = fixed USD comparison
input long InpMagic=1002001;
input datetime InpTradeFrom=D'2025.10.01';
input string InpTag="portfolio";
input int InpBrokerUtcOffsetHours=0;
input bool InpSeasonalReferenceClock=true;
input bool InpATRIncludesSignal=true;
input int InpMaximumDeviationPoints=1000;
input string InpRangeSymbol="DE30";
input string InpGoldSymbol="XAUUSD";
RRModule rangeBot,atrBot,donchianBot;
int traceFile=INVALID_HANDLE,maxOpen=0;datetime traceBar=0;
long lastRangeStamp=-1;double lastRangeBid=0,lastRangeAsk=0;
bool PortfolioMagic(long magic){return magic>=InpMagic&&magic<=InpMagic+2;}
void RefreshRisk(){double risk=InpRiskPercent>0?AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0:InpFixedRiskUSD;rangeBot.InpFixedRiskUSD=risk;atrBot.InpFixedRiskUSD=risk;donchianBot.InpFixedRiskUSD=risk;}
void Trace(){datetime now=TimeCurrent();datetime bar=now-now%300;if(now<InpTradeFrom||bar==traceBar)return;traceBar=bar;
 int a=rangeBot.PositionCount(),b=atrBot.PositionCount(),c=donchianBot.PositionCount();
 FileWrite(traceFile,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),AccountInfoDouble(ACCOUNT_MARGIN_FREE),a,b,c);
}
void RangeTick(){MqlTick q;if(!SymbolInfoTick(InpRangeSymbol,q)||q.time>TimeCurrent())return;
 if(q.time_msc!=lastRangeStamp||q.bid!=lastRangeBid||q.ask!=lastRangeAsk){lastRangeStamp=q.time_msc;lastRangeBid=q.bid;lastRangeAsk=q.ask;rangeBot.OnTick();}}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(_Symbol!=InpGoldSymbol||InpFixedRiskUSD<=0||InpRiskPercent<0||InpRiskPercent>100)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("PORTFOLIO requires hedging tester account");return INIT_FAILED;}
 if(!SymbolSelect(InpRangeSymbol,true)||!SymbolSelect(InpGoldSymbol,true))return INIT_FAILED;
 MqlRates preload[];CopyRates(InpRangeSymbol,PERIOD_M1,0,500,preload);CopyRates(InpGoldSymbol,PERIOD_H1,0,250,preload);
 rangeBot.Configure(1,InpRangeSymbol,InpFixedRiskUSD,InpMagic,InpTradeFrom,InpBrokerUtcOffsetHours,InpSeasonalReferenceClock,InpATRIncludesSignal,InpMaximumDeviationPoints);
 atrBot.Configure(2,InpGoldSymbol,InpFixedRiskUSD,InpMagic+1,InpTradeFrom,InpBrokerUtcOffsetHours,InpSeasonalReferenceClock,InpATRIncludesSignal,InpMaximumDeviationPoints);
 donchianBot.Configure(3,InpGoldSymbol,InpFixedRiskUSD,InpMagic+2,InpTradeFrom,InpBrokerUtcOffsetHours,InpSeasonalReferenceClock,InpATRIncludesSignal,InpMaximumDeviationPoints);
 if(rangeBot.Init()!=INIT_SUCCEEDED||atrBot.Init()!=INIT_SUCCEEDED||donchianBot.Init()!=INIT_SUCCEEDED)return INIT_FAILED;
 FolderCreate("ReelThree20261002",FILE_COMMON);traceFile=FileOpen("ReelThree20261002\\"+InpTag+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(traceFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(traceFile,"epoch","balance","equity","used_margin","free_margin","range_positions","atr_positions","donchian_positions");
 EventSetTimer(1);Print("PORTFOLIO shared-account native test; gold on every chart tick; range on latest DE30 tick via chart/timer; timer fallback 1 second");return INIT_SUCCEEDED;
}
void OnTick(){RefreshRisk();RangeTick();RefreshRisk();atrBot.OnTick();RefreshRisk();donchianBot.OnTick();int n=rangeBot.PositionCount()+atrBot.PositionCount()+donchianBot.PositionCount();maxOpen=MathMax(maxOpen,n);Trace();}
void OnTimer(){RefreshRisk();RangeTick();Trace();}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &rq,const MqlTradeResult &res){rangeBot.OnTradeTransaction(tx,rq,res);atrBot.OnTradeTransaction(tx,rq,res);donchianBot.OnTradeTransaction(tx,rq,res);}
struct Row{ulong id;long magic;string symbol;datetime opened,closed;int side;double vol,outvol,op,cp,profit,commission,swap,fee;};
double OnTester(){
 HistorySelect(0,TimeCurrent());Row rows[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){
  ulong deal=HistoryDealGetTicket(j);long magic=HistoryDealGetInteger(deal,DEAL_MAGIC);if(!PortfolioMagic(magic))continue;
  long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;rows[k].magic=magic;rows[k].symbol=HistoryDealGetString(deal,DEAL_SYMBOL);}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].vol+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].profit+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen("ReelThree20261002\\"+InpTag+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","gross_profit","commission","swap","fee","net_profit","magic","symbol");
 for(int k=0;k<n;k++){if(rows[k].vol<=0)continue;FileWrite(f,rows[k].id,(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].vol,rows[k].outvol,rows[k].op/rows[k].vol,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,rows[k].profit,rows[k].commission,rows[k].swap,rows[k].fee,rows[k].profit+rows[k].commission+rows[k].swap+rows[k].fee,rows[k].magic,rows[k].symbol);}
 FileClose(f);PrintFormat("PORTFOLIO_SUMMARY maxOpen=%d nativeEquityDD=%.4f",maxOpen,TesterStatistics(STAT_EQUITY_DDREL_PERCENT));return TesterStatistics(STAT_PROFIT_FACTOR);
}
void OnDeinit(const int why){EventKillTimer();if(traceFile!=INVALID_HANDLE)FileClose(traceFile);rangeBot.OnDeinit(why);atrBot.OnDeinit(why);donchianBot.OnDeinit(why);}

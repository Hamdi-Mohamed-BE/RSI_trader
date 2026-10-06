#ifndef ASIA_RESEARCH_AUDIT
#define ASIA_RESEARCH_AUDIT
#include <Trade/Trade.mqh>
input string InpAuditTag="test";
input int InpResearchManagement=0; // 0=original dual manager;1=fixed;2=stable-R;3=stable-R+DTS
input double InpResearchTrailStart=2.0;
input double InpResearchTrailDistance=0.5;
input ENUM_TIMEFRAMES InpResearchSignalTF=PERIOD_H1;
input int InpResearchLastHour=13;
input int InpResearchDirection=0; //0=both;1=long;-1=short
input int InpResearchStop=0; //0=range midpoint;1=opposite range edge
int research_events=INVALID_HANDLE,research_equity=INVALID_HANDLE,research_regimes=INVALID_HANDLE;
datetime research_signal=0,research_equity_bar=0;
double research_high=0,research_low=0;
int research_orders_failed=0,research_modify_failed=0;
long research_magic=0;
bool ResearchInit(const long magic)
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("ASIA_AUDIT_live_guard");return false;}
 research_magic=magic;
 string root="CalyxAsiaOptimize20261005\\";FolderCreate("CalyxAsiaOptimize20261005",FILE_COMMON);
 research_events=FileOpen(root+InpAuditTag+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 research_equity=FileOpen(root+InpAuditTag+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 research_regimes=FileOpen(root+InpAuditTag+"-regimes.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(research_events==INVALID_HANDLE||research_equity==INVALID_HANDLE||research_regimes==INVALID_HANDLE)return false;
 FileWrite(research_events,"position_id","epoch","side","volume","sl","tp","requested_risk","actual_risk","request_spread","signal_epoch","range_high","range_low","request_price");
 FileWrite(research_equity,"epoch","balance","equity");
 FileWrite(research_regimes,"epoch","d1_epoch","training_end","state","signal","labels","b_b","b_s","b_u","s_b","s_s","s_u","u_b","u_s","u_u");
 return InpResearchManagement>=0&&InpResearchManagement<=3&&InpResearchLastHour>=8&&InpResearchLastHour<=23&&InpResearchTrailDistance>0;
}
void ResearchEquity()
{
 datetime bar=iTime(_Symbol,PERIOD_M15,0);
 if(bar==research_equity_bar)return;
 research_equity_bar=bar;FileWrite(research_equity,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
}
bool ResearchOrder(CTrade &client,const int side,const double lots,const string symbol,const double sl,const double tp,const double risk,const string comment)
{
 MqlTick tick;SymbolInfoTick(symbol,tick);double requested=AccountInfoDouble(ACCOUNT_EQUITY)*risk/100.0;
 bool ok=(side>0?client.Buy(lots,symbol,0.0,sl,tp,comment):client.Sell(lots,symbol,0.0,sl,tp,comment));
 if(!ok||client.ResultRetcode()!=TRADE_RETCODE_DONE){research_orders_failed++;return ok;}
 ulong deal=client.ResultDeal();if(!HistoryDealSelect(deal)){Print("ASIA_AUDIT_entry_deal_missing");return ok;}
 ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
 double fill=HistoryDealGetDouble(deal,DEAL_PRICE),actual=0;
 if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,symbol,lots,fill,sl,actual))Print("ASIA_AUDIT_risk_missing");
 FileWrite(research_events,id,(long)TimeCurrent(),side,DoubleToString(lots,8),DoubleToString(sl,8),DoubleToString(tp,8),DoubleToString(requested,8),DoubleToString(MathAbs(actual),8),DoubleToString(tick.ask-tick.bid,8),(long)research_signal,DoubleToString(research_high,8),DoubleToString(research_low,8),DoubleToString(side>0?tick.ask:tick.bid,8));
 return ok;
}
void ResearchStableTrail(const long magic,const double rr)
{
 if(InpResearchManagement!=2&&InpResearchManagement!=3)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 CTrade client;client.SetExpertMagicNumber((ulong)magic);
 double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point+step;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);if(ticket==0||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=magic)continue;
  double open=PositionGetDouble(POSITION_PRICE_OPEN),tp=PositionGetDouble(POSITION_TP),sl=PositionGetDouble(POSITION_SL);
  double original=MathAbs(tp-open)/rr;int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
  double price=side>0?tick.bid:tick.ask;if(original<=0||side*(price-open)<InpResearchTrailStart*original)continue;
  double candidate=price-side*InpResearchTrailDistance*original;
  candidate=side>0?MathMin(candidate,price-gap):MathMax(candidate,price+gap);
  candidate=(side>0?MathFloor(candidate/step):MathCeil(candidate/step))*step;
  if(side*(candidate-sl)<step)continue;
  if(!client.PositionModify(ticket,candidate,tp)||client.ResultRetcode()!=TRADE_RETCODE_DONE)research_modify_failed++;
 }
}
void ResearchClose()
{
 HistorySelect(0,TimeCurrent());string root="CalyxAsiaOptimize20261005\\";
 int f=FileOpen(root+InpAuditTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","comment");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);if(HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(d,DEAL_MAGIC)!=research_magic)continue;
  FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),HistoryDealGetString(d,DEAL_COMMENT));
 }
 FileWrite(research_equity,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
 FileClose(f);FileClose(research_events);FileClose(research_equity);FileClose(research_regimes);
 PrintFormat("ASIA_SUMMARY orders_failed=%d modify_failed=%d",research_orders_failed,research_modify_failed);
}
#endif

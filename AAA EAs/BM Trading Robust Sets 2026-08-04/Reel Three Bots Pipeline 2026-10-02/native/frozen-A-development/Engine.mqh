#include <Trade/Trade.mqh>
// Generated from frozen ReelRules.mqh; build_portfolio.py documents mechanical changes.
class RRModule {
public:
#include "Extensions.mqh"
string m_symbol;int m_digits;int BOT;
double InpFixedRiskUSD;
long InpMagic;
datetime InpTradeFrom;
string InpTag;
int InpBrokerUtcOffsetHours;
bool InpSeasonalReferenceClock; // range: UTC+2 winter, UTC+3 EU summer
bool InpATRIncludesSignal;
int InpMaximumDeviationPoints;
RRModule(){InpFixedRiskUSD=100.0;InpMagic=1002001;InpTradeFrom=D'2025.10.01';InpTag="range";InpBrokerUtcOffsetHours=0;InpSeasonalReferenceClock=true;InpATRIncludesSignal=true;InpMaximumDeviationPoints=1000;lastBar=0;lastDay=0;traceBar=0;dailyDone=false;buyArmed=true;sellArmed=true;atrHandle=INVALID_HANDLE;traceFile=INVALID_HANDLE;candidates=0;entries=0;entryFails=0;modifyFails=0;closeFails=0;sizeSkips=0;dataSkips=0;existingSkips=0;expiredSkips=0;ocoRaces=0;tickSize=0;minLot=0;lotStep=0;}
void Configure(int kind,string symbol,double risk,long magic,datetime start,int offset,bool seasonal,bool atrIncludes,int deviation){
 BOT=kind;m_symbol=symbol;m_digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
 InpFixedRiskUSD=risk;InpMagic=magic;InpTradeFrom=start;InpBrokerUtcOffsetHours=offset;
 InpSeasonalReferenceClock=seasonal;InpATRIncludesSignal=atrIncludes;InpMaximumDeviationPoints=deviation;
}
int PositionCount(){return CountPositions();}
CTrade trade;
datetime lastBar,lastDay,traceBar;
bool dailyDone,buyArmed,sellArmed;
int atrHandle,traceFile;
int candidates,entries,entryFails,modifyFails,closeFails,sizeSkips,dataSkips,existingSkips,expiredSkips,ocoRaces;
double tickSize,minLot,lotStep;
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,m_digits);}
bool OwnPos(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket&&PositionGetInteger(POSITION_MAGIC)==InpMagic&&PositionGetString(POSITION_SYMBOL)==m_symbol)return true;}ticket=0;return false;}
int CountPositions(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&PositionGetInteger(POSITION_MAGIC)==InpMagic&&PositionGetString(POSITION_SYMBOL)==m_symbol)n++;}return n;}
void CancelOrders(){for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t&&OrderGetInteger(ORDER_MAGIC)==InpMagic&&OrderGetString(ORDER_SYMBOL)==m_symbol){if(!trade.OrderDelete(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){cancelFails++;PrintFormat("RP_CANCEL_FAIL %u",trade.ResultRetcode());}}}}

void Flat(){CancelOrders();for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&PositionGetInteger(POSITION_MAGIC)==InpMagic&&PositionGetString(POSITION_SYMBOL)==m_symbol){if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("RR_CLOSE_FAIL %u",trade.ResultRetcode());}}}}
int LastSunday(int year,int month){MqlDateTime d={};d.year=year;d.mon=month+1;d.day=1;datetime t=StructToTime(d)-86400;TimeToStruct(t,d);return d.day-d.day_of_week;}
int RefOffset(datetime utc){if(!InpSeasonalReferenceClock)return 0;MqlDateTime d;TimeToStruct(utc,d);int y=d.year;d.mon=3;d.day=LastSunday(y,3);d.hour=1;d.min=0;d.sec=0;datetime a=StructToTime(d);d.mon=10;d.day=LastSunday(y,10);datetime b=StructToTime(d);return utc>=a&&utc<b?3:2;}
datetime ReferenceTime(datetime srv){datetime utc=srv-InpBrokerUtcOffsetHours*3600;return utc+RefOffset(utc)*3600;}
double Lots(int side,double entry,double sl){double cash=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,m_symbol,1.0,entry,sl,cash)||cash>=0){sizeSkips++;return 0;}double v=NormalizeDouble(MathFloor((InpFixedRiskUSD/-cash+1e-10)/lotStep)*lotStep,8);if(v<minLot||v>SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MAX)){sizeSkips++;return 0;}return v;}
bool ValidStops(int side,double sl,double tp,const MqlTick &q){double gap=MathMax(tickSize,SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(m_symbol,SYMBOL_POINT)),ref=side>0?q.bid:q.ask;return side*(ref-sl)>=gap&&(tp==0||side*(tp-ref)>=gap);}
bool Market(int side,double sl,double tp,string why){return Execute(side,sl,tp,why);}

void Range(datetime now){RangeFeature(now);}

void AtrCandle(datetime now){
 datetime current=iTime(m_symbol,TF(),0);if(current<=0||current==lastBar)return;
 MqlRates r[];if(CopyRates(m_symbol,TF(),1,1,r)!=1){dataSkips++;return;}
 double av[];int shift=InpATRIncludesSignal?1:2;if(CopyBuffer(atrHandle,0,shift,1,av)!=1){dataSkips++;return;}
 lastBar=current;if(now<InpTradeFrom||now-current>=300)return;
 double range=r[0].high-r[0].low;if(range<=0||av[0]<=0||range<=P(20)*av[0])return;
 int side=0;if(r[0].close>r[0].open&&r[0].close>=r[0].high-P(21)*range)side=1;if(r[0].close<r[0].open&&r[0].close<=r[0].low+P(21)*range)side=-1;
 if(side==0)return;candidates++;lastRuleSide=side;if(Control)side=RandSide(now);if(CountPositions()>=(int)P(25)){existingSkips++;return;}
 double sl=Price(r[0].close*(1-side*P(5)/100)),tp=P(6)>0?Price(r[0].close*(1+side*P(5)*P(6)/100)):0;Market(side,sl,tp,"RR ATR Candle");
}
void Donchian(datetime now){DonFeature(now);}

void DonchianTrail(){for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(!t||PositionGetInteger(POSITION_MAGIC)!=InpMagic||PositionGetString(POSITION_SYMBOL)!=m_symbol)continue;MqlTick q;if(!SymbolInfoTick(m_symbol,q))return;int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double entry=PositionGetDouble(POSITION_PRICE_OPEN),px=side>0?q.bid:q.ask;if(side*(px-entry)<.005*entry)continue;double want=Price(px-side*.001*entry),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);if(side*(want-sl)<=tickSize/2||!ValidStops(side,want,tp,q))continue;bool changed=trade.PositionModify(t,want,tp);if(changed&&trade.ResultRetcode()==TRADE_RETCODE_DONE)trailCount++;else if(trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES){modifyFails++;if(modifyFails<=10)PrintFormat("RR_MODIFY_FAIL %u",trade.ResultRetcode());}}}
int Init(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: use Strategy Tester; live deployment not approved");return INIT_FAILED;}
 if(InpFixedRiskUSD<=0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(m_symbol,SYMBOL_TRADE_TICK_SIZE);minLot=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MIN);lotStep=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_STEP);if(tickSize<=0||minLot<=0||lotStep<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(m_symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
 if(BOT==2){atrHandle=iATR(m_symbol,TF(),(int)P(28));if(atrHandle==INVALID_HANDLE)return INIT_FAILED;}
 
 PrintFormat("RR_SPEC bot=%d symbol=%s broker=%s server=%s min=%.8f step=%.8f contract=%.8f fixed_risk=%.2f",BOT,m_symbol,AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),minLot,lotStep,SymbolInfoDouble(m_symbol,SYMBOL_TRADE_CONTRACT_SIZE),InpFixedRiskUSD);return INIT_SUCCEEDED;
}
void OnTick(){datetime now=TimeCurrent();Manage();if(BOT==1)Range(now);if(BOT==2)AtrCandle(now);if(BOT==3){if((int)P(7)==9)DonchianTrail();Donchian(now);}}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &rq,const MqlTradeResult &res){if(tx.type==TRADE_TRANSACTION_DEAL_ADD&&HistoryDealSelect(tx.deal)&&HistoryDealGetInteger(tx.deal,DEAL_MAGIC)==InpMagic&&HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_IN){entries++;dayEntries++;Capture();if(BOT==3){if(lastRuleSide>0)buyArmed=false;else if(lastRuleSide<0)sellArmed=false;}if(BOT==1){dailyDone=true;CancelOrders();}}}
void OnDeinit(const int why){ReleaseFeatures();if(atrHandle!=INVALID_HANDLE)IndicatorRelease(atrHandle);if(traceFile!=INVALID_HANDLE)FileClose(traceFile);PrintFormat("RR_SUMMARY candidates=%d entries=%d entryFails=%d modifyFails=%d closeFails=%d sizeSkips=%d dataSkips=%d existingSkips=%d expiredSkips=%d ocoRaces=%d",candidates,entries,entryFails,modifyFails,closeFails,sizeSkips,dataSkips,existingSkips,expiredSkips,ocoRaces);}

};

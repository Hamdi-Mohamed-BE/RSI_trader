#include <Trade/Trade.mqh>
// Generated from frozen ReelRules.mqh; build_portfolio.py documents mechanical changes.
class RRModule {
public:
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
void CancelOrders(){for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t&&OrderGetInteger(ORDER_MAGIC)==InpMagic&&OrderGetString(ORDER_SYMBOL)==m_symbol){if(!trade.OrderDelete(t))PrintFormat("RR_CANCEL_FAIL %u",trade.ResultRetcode());}}}
void Flat(){CancelOrders();for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&PositionGetInteger(POSITION_MAGIC)==InpMagic&&PositionGetString(POSITION_SYMBOL)==m_symbol){if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("RR_CLOSE_FAIL %u",trade.ResultRetcode());}}}}
int LastSunday(int year,int month){MqlDateTime d={};d.year=year;d.mon=month+1;d.day=1;datetime t=StructToTime(d)-86400;TimeToStruct(t,d);return d.day-d.day_of_week;}
int RefOffset(datetime utc){if(!InpSeasonalReferenceClock)return 0;MqlDateTime d;TimeToStruct(utc,d);int y=d.year;d.mon=3;d.day=LastSunday(y,3);d.hour=1;d.min=0;d.sec=0;datetime a=StructToTime(d);d.mon=10;d.day=LastSunday(y,10);datetime b=StructToTime(d);return utc>=a&&utc<b?3:2;}
datetime ReferenceTime(datetime srv){datetime utc=srv-InpBrokerUtcOffsetHours*3600;return utc+RefOffset(utc)*3600;}
double Lots(int side,double entry,double sl){double cash=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,m_symbol,1.0,entry,sl,cash)||cash>=0){sizeSkips++;return 0;}double v=NormalizeDouble(MathFloor((InpFixedRiskUSD/-cash+1e-10)/lotStep)*lotStep,8);if(v<minLot||v>SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MAX)){sizeSkips++;return 0;}return v;}
bool ValidStops(int side,double sl,double tp,const MqlTick &q){double gap=MathMax(tickSize,SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point),ref=side>0?q.bid:q.ask;return side*(ref-sl)>=gap&&(tp==0||side*(tp-ref)>=gap);}
bool Market(int side,double sl,double tp,string why){MqlTick q;if(!SymbolInfoTick(m_symbol,q))return false;double entry=side>0?q.ask:q.bid,v=Lots(side,entry,sl);if(v<=0||!ValidStops(side,sl,tp,q))return false;bool ok=side>0?trade.Buy(v,m_symbol,0,sl,tp,why):trade.Sell(v,m_symbol,0,sl,tp,why);if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){entryFails++;PrintFormat("RR_ENTRY_FAIL %u %s",trade.ResultRetcode(),why);return false;}return true;}
void Range(datetime now){
 datetime rt=ReferenceTime(now),day=rt-rt%86400;int sec=(int)(rt-day);MqlDateTime d;TimeToStruct(rt,d);
 if(day!=lastDay){lastDay=day;dailyDone=false;}
 ulong t;if(OwnPos(t)){dailyDone=true;CancelOrders();if(CountPositions()>1)ocoRaces++;}
 if(sec>=18*3600){Flat();dailyDone=true;return;}
 if(now<InpTradeFrom||d.day_of_week==0||d.day_of_week==6||dailyDone||sec<11*3600)return;
 if(sec>=11*3600+300){dailyDone=true;expiredSkips++;return;}
 int off=RefOffset(now-InpBrokerUtcOffsetHours*3600)-InpBrokerUtcOffsetHours;
 datetime start=day+8*3600-off*3600,end=day+11*3600-off*3600;
 MqlRates r[];int n=CopyRates(m_symbol,PERIOD_M1,start,end-1,r);if(n<=0){dataSkips++;return;}
 double high=-DBL_MAX,low=DBL_MAX;for(int i=0;i<n;i++){high=MathMax(high,r[i].high);low=MathMin(low,r[i].low);}high=Price(high);low=Price(low);
 dailyDone=true;candidates++;MqlTick q;if(!SymbolInfoTick(m_symbol,q)||high<=low)return;
 double gap=MathMax(tickSize,SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);
 if(high-q.ask<gap||q.bid-low<gap){Print("RR_RANGE_SKIP already crossed/stop placement too close");return;}
 double bv=Lots(1,high,low),sv=Lots(-1,low,high);if(bv<=0||sv<=0)return;
 datetime expiry=day+18*3600-off*3600;
 bool b=trade.BuyStop(bv,high,m_symbol,low,0,ORDER_TIME_SPECIFIED,expiry,"RR Range Buy");uint bc=trade.ResultRetcode();
 bool s=false;if(b&&(bc==TRADE_RETCODE_PLACED||bc==TRADE_RETCODE_DONE))s=trade.SellStop(sv,low,m_symbol,high,0,ORDER_TIME_SPECIFIED,expiry,"RR Range Sell");
 uint sc=trade.ResultRetcode();if(!b||!s||(sc!=TRADE_RETCODE_PLACED&&sc!=TRADE_RETCODE_DONE)){entryFails++;PrintFormat("RR_RANGE_ENTRY_FAIL buy=%u sell=%u",bc,sc);CancelOrders();}
}
void AtrCandle(datetime now){
 datetime current=iTime(m_symbol,PERIOD_H1,0);if(current<=0||current==lastBar)return;
 MqlRates r[];if(CopyRates(m_symbol,PERIOD_H1,1,1,r)!=1){dataSkips++;return;}
 double av[];int shift=InpATRIncludesSignal?1:2;if(CopyBuffer(atrHandle,0,shift,1,av)!=1){dataSkips++;return;}
 lastBar=current;if(now<InpTradeFrom||now-current>=300)return;
 double range=r[0].high-r[0].low;if(range<=0||av[0]<=0||range<=2.5*av[0])return;
 int side=0;if(r[0].close>r[0].open&&r[0].close>=r[0].high-.25*range)side=1;if(r[0].close<r[0].open&&r[0].close<=r[0].low+.25*range)side=-1;
 if(side==0)return;candidates++;ulong t;if(OwnPos(t)){existingSkips++;return;}
 double sl=Price(r[0].close*(1-side*.005)),tp=Price(r[0].close*(1+side*.035));Market(side,sl,tp,"RR ATR Candle");
}
void Donchian(datetime now){
 datetime current=iTime(m_symbol,PERIOD_M1,0);if(current<=0||current==lastBar)return;
 MqlRates h[],m[];if(CopyRates(m_symbol,PERIOD_H1,1,175,h)!=175||CopyRates(m_symbol,PERIOD_M1,1,2,m)!=2){dataSkips++;return;}
 lastBar=current;double hi=-DBL_MAX,lo=DBL_MAX;for(int i=0;i<175;i++){hi=MathMax(hi,h[i].high);lo=MathMin(lo,h[i].low);}double mid=(hi+lo)/2;
 if(m[0].close>=mid&&m[1].close<mid)buyArmed=true;
 if(m[0].close<=mid&&m[1].close>mid)sellArmed=true;
 if(now<InpTradeFrom||now-current>=60)return;
 int side=0;if(buyArmed&&m[1].close>hi)side=1;else if(sellArmed&&m[1].close<lo)side=-1;if(!side)return;
 candidates++;ulong t;if(OwnPos(t)){existingSkips++;return;}MqlTick q;if(!SymbolInfoTick(m_symbol,q))return;double entry=side>0?q.ask:q.bid;
 if(Market(side,Price(entry*(1-side*.005)),Price(entry*(1+side*.01)),"RR Donchian")){if(side>0)buyArmed=false;else sellArmed=false;}
}
void DonchianTrail(){for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(!t||PositionGetInteger(POSITION_MAGIC)!=InpMagic||PositionGetString(POSITION_SYMBOL)!=m_symbol)continue;MqlTick q;if(!SymbolInfoTick(m_symbol,q))return;int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double entry=PositionGetDouble(POSITION_PRICE_OPEN),px=side>0?q.bid:q.ask;if(side*(px-entry)<.005*entry)continue;double want=Price(px-side*.001*entry),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);if(side*(want-sl)<=tickSize/2||!ValidStops(side,want,tp,q))continue;if(!trade.PositionModify(t,want,tp)&&trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES){modifyFails++;if(modifyFails<=10)PrintFormat("RR_MODIFY_FAIL %u",trade.ResultRetcode());}}}
int Init(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: use Strategy Tester; live deployment not approved");return INIT_FAILED;}
 if(InpFixedRiskUSD<=0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(m_symbol,SYMBOL_TRADE_TICK_SIZE);minLot=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_MIN);lotStep=SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_STEP);if(tickSize<=0||minLot<=0||lotStep<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(m_symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
 if(BOT==2){atrHandle=iATR(m_symbol,PERIOD_H1,200);if(atrHandle==INVALID_HANDLE)return INIT_FAILED;}
 
 FileWrite(traceFile,"epoch","balance","equity");PrintFormat("RR_SPEC bot=%d symbol=%s broker=%s server=%s min=%.8f step=%.8f contract=%.8f fixed_risk=%.2f",BOT,m_symbol,AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),minLot,lotStep,SymbolInfoDouble(m_symbol,SYMBOL_TRADE_CONTRACT_SIZE),InpFixedRiskUSD);return INIT_SUCCEEDED;
}
void OnTick(){datetime now=TimeCurrent();if(BOT==1)Range(now);if(BOT==2)AtrCandle(now);if(BOT==3){DonchianTrail();Donchian(now);}}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &rq,const MqlTradeResult &res){if(tx.type==TRADE_TRANSACTION_DEAL_ADD&&HistoryDealSelect(tx.deal)&&HistoryDealGetInteger(tx.deal,DEAL_MAGIC)==InpMagic&&HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_IN){entries++;if(BOT==1){dailyDone=true;CancelOrders();}}}
void OnDeinit(const int why){if(atrHandle!=INVALID_HANDLE)IndicatorRelease(atrHandle);if(traceFile!=INVALID_HANDLE)FileClose(traceFile);PrintFormat("RR_SUMMARY candidates=%d entries=%d entryFails=%d modifyFails=%d closeFails=%d sizeSkips=%d dataSkips=%d existingSkips=%d expiredSkips=%d ocoRaces=%d",candidates,entries,entryFails,modifyFails,closeFails,sizeSkips,dataSkips,existingSkips,expiredSkips,ocoRaces);}

};

#property strict
#property version "1.00"
#property description "Research-only mechanical reconstruction. No SL, no individual TP, uncapped grid. Refuses live trading."
#include <Trade/Trade.mqh>

input ENUM_TIMEFRAMES InpSignalTF=PERIOD_M5;
input int InpEMAPeriod=5;
input double InpStartingLot=0.01;
input double InpLotIncrement=0.01;
input int InpGridPoints=300;
input double InpBasketTargetUSD=10.0;
input bool InpAlternateAfterBasket=true;
input long InpMagicBase=261010000;
input string InpGridAuditTag="";

CTrade trade;
int ema=INVALID_HANDLE,signalsFile=INVALID_HANDLE,traceFile=INVALID_HANDLE;
datetime seenBar=0,lastTrace=0,dailyDay=0;
int basket=0,side=0,nextSide=0,orders=0,knownCount=0;
double startBalance=0,openingFees=0,knownLots=0;
bool closing=false,stopoutSeen=false;
string closeReason="";
long signalCount=0,spacingSkips=0,directionSkips=0,rejected=0,closeFailures=0,stopoutDeals=0;
double equityPeak=10000,maxEquityDD=0,maxEquityDDPct=0,dailyPeak=10000,maxDailyDD=0;
double maxLots=0,maxMargin=0,minFloating=0;
int maxPositions=0;

string Path(const string suffix){return "CalyxEURGridRaw20261010\\"+InpGridAuditTag+"-"+suffix+".csv";}
long Magic(){return InpMagicBase+basket;}

void RefreshExposure()
{
 knownCount=0;knownLots=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=Magic())continue;
  knownCount++;knownLots+=PositionGetDouble(POSITION_VOLUME);
 }
 maxPositions=MathMax(maxPositions,knownCount);maxLots=MathMax(maxLots,knownLots);
}

void Observe()
{
 double eq=AccountInfoDouble(ACCOUNT_EQUITY),bal=AccountInfoDouble(ACCOUNT_BALANCE);
 equityPeak=MathMax(equityPeak,eq);
 maxEquityDD=MathMax(maxEquityDD,equityPeak-eq);
 if(equityPeak>0)maxEquityDDPct=MathMax(maxEquityDDPct,100*(equityPeak-eq)/equityPeak);
 datetime day=(datetime)((long)TimeCurrent()/86400*86400);
 if(day!=dailyDay){dailyDay=day;dailyPeak=eq;}
 dailyPeak=MathMax(dailyPeak,eq);maxDailyDD=MathMax(maxDailyDD,dailyPeak-eq);
 maxMargin=MathMax(maxMargin,AccountInfoDouble(ACCOUNT_MARGIN));
 minFloating=MathMin(minFloating,eq-bal);
 if(traceFile!=INVALID_HANDLE && (lastTrace==0 || TimeCurrent()/60!=lastTrace/60))
 {
  lastTrace=TimeCurrent();
  FileWrite(traceFile,(long)TimeCurrent(),DoubleToString(bal,2),DoubleToString(eq,2),basket,knownCount,
   DoubleToString(knownLots,2),DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN),2));
 }
}

double NearestDistance(const double price)
{
 double nearest=DBL_MAX;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=Magic())continue;
  nearest=MathMin(nearest,MathAbs(price-PositionGetDouble(POSITION_PRICE_OPEN))/_Point);
 }
 return nearest;
}

void FinishBasket()
{
 PrintFormat("GRID_BASKET_END id=%d side=%d orders=%d cash=%.2f reason=%s",basket,side,orders,
  AccountInfoDouble(ACCOUNT_BALANCE)-startBalance,closeReason==""?"EXTERNAL":closeReason);
 nextSide=InpAlternateAfterBasket?-side:0;
 side=0;orders=0;openingFees=0;closing=false;closeReason="";
}

void CloseBasket()
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=Magic())continue;
  if(!trade.PositionClose(ticket) || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))closeFailures++;
 }
 RefreshExposure();if(knownCount==0)FinishBasket();
}

int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research EA: live use disabled");return INIT_FAILED;}
 if(_Symbol!="EURUSD" || AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING ||
  InpGridAuditTag=="" || InpStartingLot<=0 || InpLotIncrement<0 || InpGridPoints<=0 || InpBasketTargetUSD<=0)return INIT_PARAMETERS_INCORRECT;
 ema=iMA(_Symbol,InpSignalTF,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
 if(ema==INVALID_HANDLE)return INIT_FAILED;
 trade.SetAsyncMode(false);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 FolderCreate("CalyxEURGridRaw20261010",FILE_COMMON);
 signalsFile=FileOpen(Path("signals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 traceFile=FileOpen(Path("trace"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(signalsFile==INVALID_HANDLE || traceFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(signalsFile,"basket","order_index","epoch","signal_start","signal_close","side","v_old","v_mid","v_new","close","ema","nearest_points","lots","fill_price","deal","magic");
 FileWrite(traceFile,"epoch","balance","equity","basket","positions","lots","margin");
 seenBar=iTime(_Symbol,InpSignalTF,0);equityPeak=AccountInfoDouble(ACCOUNT_EQUITY);
 PrintFormat("GRID_CONFIG digits=%d point=%.8f grid_pips=%.2f leverage=%d stopout_level=%.2f stopout_mode=%d lot_min=%.2f lot_step=%.2f",
  _Digits,_Point,InpGridPoints/10.0,AccountInfoInteger(ACCOUNT_LEVERAGE),AccountInfoDouble(ACCOUNT_MARGIN_SO_SO),
  AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
 return INIT_SUCCEEDED;
}

void OnTick()
{
 Observe();
 if(side!=0)
 {
  if(PositionsTotal()!=knownCount)RefreshExposure();
  if(knownCount==0){FinishBasket();return;}
  // Equity already includes realised entry costs and swap. Reserve the same
  // commission/fee again for closing; this is an estimate, not a guaranteed fill.
  double projectedNet=AccountInfoDouble(ACCOUNT_EQUITY)-startBalance-openingFees;
  if(closing || projectedNet>=InpBasketTargetUSD)
  {closing=true;if(closeReason=="")closeReason="TARGET";CloseBasket();Observe();return;}
 }
 datetime bar=iTime(_Symbol,InpSignalTF,0);
 if(bar==0 || bar==seenBar)return;
 seenBar=bar;
 MqlRates r[3];double e[1];
 if(CopyRates(_Symbol,InpSignalTF,1,3,r)!=3 || CopyBuffer(ema,0,1,1,e)!=1)return;
 int seconds=PeriodSeconds(InpSignalTF);
 if(r[2].time+seconds!=bar || !MathIsValidNumber(e[0]))return;
 if(!(r[0].tick_volume<r[1].tick_volume && r[1].tick_volume<r[2].tick_volume))return;
 int dir=r[2].close>e[0]?1:(r[2].close<e[0]?-1:0);
 if(dir==0)return;signalCount++;
 if((side!=0 && dir!=side) || (side==0 && nextSide!=0 && dir!=nextSide)){directionSkips++;return;}
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double requestedPrice=dir>0?tick.ask:tick.bid;
 double nearest=side==0?DBL_MAX:NearestDistance(requestedPrice);
 if(nearest+1e-7<InpGridPoints){spacingSkips++;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 double lots=NormalizeDouble(MathFloor((InpStartingLot+InpLotIncrement*orders+1e-10)/step)*step,8);
 if(lots<minimum || lots>maximum){rejected++;return;}
 bool newBasket=side==0;
 if(newBasket){basket++;side=dir;startBalance=AccountInfoDouble(ACCOUNT_BALANCE);openingFees=0;orders=0;}
 trade.SetExpertMagicNumber((ulong)Magic());
 string comment=StringFormat("GRID B%d N%d",basket,orders+1);
 bool sent=dir>0?trade.Buy(lots,_Symbol,0,0,0,comment):trade.Sell(lots,_Symbol,0,0,0,comment);
 if(!sent || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
 {
  rejected++;if(newBasket){basket--;side=0;}return;
 }
 orders++;
 ulong deal=trade.ResultDeal();
 if(HistoryDealSelect(deal))openingFees+=MathMax(0,-HistoryDealGetDouble(deal,DEAL_COMMISSION)-HistoryDealGetDouble(deal,DEAL_FEE));
 FileWrite(signalsFile,basket,orders,(long)TimeCurrent(),(long)r[2].time,(long)(r[2].time+seconds),dir,
  r[0].tick_volume,r[1].tick_volume,r[2].tick_volume,DoubleToString(r[2].close,8),DoubleToString(e[0],8),
  nearest==DBL_MAX?"":DoubleToString(nearest,4),DoubleToString(lots,8),DoubleToString(trade.ResultPrice(),8),deal,Magic());
 RefreshExposure();Observe();
}

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(trans.deal))return;
 if(HistoryDealGetInteger(trans.deal,DEAL_REASON)==DEAL_REASON_SO)
 {stopoutDeals++;stopoutSeen=true;closeReason="STOPOUT";}
}

void OnDeinit(const int reason)
{
 Observe();
 if(signalsFile!=INVALID_HANDLE){FileClose(signalsFile);signalsFile=INVALID_HANDLE;}
 if(traceFile!=INVALID_HANDLE)
 {
  FileWrite(traceFile,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),basket,knownCount,DoubleToString(knownLots,2),DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN),2));
  FileClose(traceFile);traceFile=INVALID_HANDLE;
 }
 int f=FileOpen(Path("stats"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f!=INVALID_HANDLE)
 {
  FileWrite(f,"metric","value");
  FileWrite(f,"max_equity_dd_usd",maxEquityDD);FileWrite(f,"max_equity_dd_pct",maxEquityDDPct);
  FileWrite(f,"max_daily_equity_dd_usd",maxDailyDD);FileWrite(f,"worst_floating_pnl_usd",minFloating);
  FileWrite(f,"max_positions",maxPositions);FileWrite(f,"max_lots",maxLots);FileWrite(f,"max_margin_usd",maxMargin);
  FileWrite(f,"signals",signalCount);FileWrite(f,"spacing_skips",spacingSkips);FileWrite(f,"direction_skips",directionSkips);
  FileWrite(f,"rejected_entries",rejected);FileWrite(f,"close_failures",closeFailures);FileWrite(f,"stopout_deals",stopoutDeals);
  FileWrite(f,"digits",_Digits);FileWrite(f,"point",_Point);FileWrite(f,"grid_points",InpGridPoints);
  FileClose(f);
 }
 if(ema!=INVALID_HANDLE)IndicatorRelease(ema);
 PrintFormat("GRID_STATS baskets=%d max_positions=%d max_lots=%.2f equityDD=%.2f rejected=%d stopout=%s",basket,maxPositions,maxLots,maxEquityDD,rejected,stopoutSeen?"true":"false");
}

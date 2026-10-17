// Tester-only research accounting and account-rule policy. Not a deployment file.
input int InpCase=0; // 0 shared, 1 Nasdaq, 2 RSI VWAP, 3 EMA3
input bool InpNasdaqDI=false;
input bool InpChallenge=false;
input int InpPhase=1;
input string InpTag="ftmo3";
input long InpTradingFromEpoch=0;
const double InitialCapital=10000.0;
int auditFile=INVALID_HANDLE,eventFile=INVALID_HANDLE,admitFile=INVALID_HANDLE;
int dayFile=INVALID_HANDLE,contractFile=INVALID_HANDLE;
int observedDay=0; datetime firstObserved=0,lastObserved=0,lastMinute=0;
double dayAnchor=10000,dayMinimum=10000,dayMaxLoss=0,dayPeakEquity=10000,dayPeakToTrough=0;
double overallPeak=10000,observedDDCash=0,observedDDPct=0,maxMarginProxy=0;
int maximumPositions=0,entryDays[];
int officialStatus=0; // 0 running, 1 natural pass, -1 daily fail, -2 static fail
datetime statusEpoch=0; double statusEquity=0,statusBalance=0,statusAnchor=0;
long seenUSTEC=-1,seenGold=-1; bool insidePump=false,liquidating=false,forcedFinalization=false;
double ledgerBalance=-1;int ledgerDay=0;
bool PortfolioOrderSend(const MqlTradeRequest &request,MqlTradeResult &result);
class CPortfolioTrade:public CTrade
{
 public:
 virtual bool OrderSend(const MqlTradeRequest &request,MqlTradeResult &result)
 {return PortfolioOrderSend(request,result);}
};
string AuditPath(const string suffix){return "FTMO3_20261016_"+InpTag+"-"+suffix+".csv";}
bool Active(const int i){return InpCase==0 || InpCase==i;}
datetime LastSundayUTC(const int year,const int month)
{
 MqlDateTime t={};t.year=year;t.mon=month;t.day=31;t.hour=1;
 datetime d=StructToTime(t);TimeToStruct(d,t);return d-t.day_of_week*86400;
}
int PragueOffset(const datetime utc)
{
 MqlDateTime t={};TimeToStruct(utc,t);
 return utc>=LastSundayUTC(t.year,3) && utc<LastSundayUTC(t.year,10)?7200:3600;
}
int PragueDay(const datetime utc)
{
 MqlDateTime t={};TimeToStruct(utc+PragueOffset(utc),t);return t.year*10000+t.mon*100+t.day;
}
double DealCash(const ulong d)
{
 return HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
}
void AppendEntryDay(const int day)
{
 for(int i=0;i<ArraySize(entryDays);i++)if(entryDays[i]==day)return;
 int n=ArraySize(entryDays);ArrayResize(entryDays,n+1);entryDays[n]=day;
}
bool RefreshLedger(const bool force=false)
{
 if(!force && ledgerDay==PragueDay(TimeCurrent()) && ledgerBalance==AccountInfoDouble(ACCOUNT_BALANCE))return true;
 if(!HistorySelect(0,TimeCurrent()+86400))return false;
 double delta=0;int today=PragueDay(TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);
  if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
  datetime t=(datetime)HistoryDealGetInteger(d,DEAL_TIME);
  if(PragueDay(t)==today)delta+=DealCash(d);
  long entry=HistoryDealGetInteger(d,DEAL_ENTRY);
  if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)AppendEntryDay(PragueDay(t));
 }
 dayAnchor=AccountInfoDouble(ACCOUNT_BALANCE)-delta;ledgerBalance=AccountInfoDouble(ACCOUNT_BALANCE);ledgerDay=today;return dayAnchor>0;
}
void Event(const string kind,const string info)
{
 if(eventFile!=INVALID_HANDLE)FileWrite(eventFile,(long)TimeCurrent(),PragueDay(TimeCurrent()),kind,officialStatus,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),DoubleToString(dayAnchor,2),ArraySize(entryDays),PositionsTotal(),OrdersTotal(),info);
}
void WriteDay()
{
 if(observedDay>0 && dayFile!=INVALID_HANDLE)FileWrite(dayFile,observedDay,DoubleToString(dayAnchor,2),DoubleToString(dayMinimum,2),DoubleToString(dayMaxLoss,2),DoubleToString(dayPeakToTrough,2),DoubleToString(dayAnchor-500,2));
}
double MarginProxy()
{
 double gross=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  if(PositionGetTicket(i)==0)continue;string s=PositionGetString(POSITION_SYMBOL);MqlTick t={};
  if(!SymbolInfoTick(s,t))return DBL_MAX;
  gross+=PositionGetDouble(POSITION_VOLUME)*SymbolInfoDouble(s,SYMBOL_TRADE_CONTRACT_SIZE)*MathMax(t.ask,t.bid)/15.0;
 }
 for(int i=OrdersTotal()-1;i>=0;i--)
 {
  if(OrderGetTicket(i)==0)continue;string s=OrderGetString(ORDER_SYMBOL);
  gross+=OrderGetDouble(ORDER_VOLUME_CURRENT)*SymbolInfoDouble(s,SYMBOL_TRADE_CONTRACT_SIZE)*OrderGetDouble(ORDER_PRICE_OPEN)/15.0;
 }
 return gross;
}
void Observe(const bool permitPass=true)
{
 if(!MQLInfoInteger(MQL_TESTER) || forcedFinalization)return;
 datetime now=TimeCurrent();if(now<=0)return;
 if(firstObserved==0)firstObserved=now;lastObserved=now;
 int day=PragueDay(now);double equity=AccountInfoDouble(ACCOUNT_EQUITY);
 if(day!=observedDay)
 {
  WriteDay();observedDay=day;
  if(!RefreshLedger()){officialStatus=-3;statusEpoch=now;Event("ledger_failure","No new entries permitted");return;}
  dayMinimum=equity;dayMaxLoss=MathMax(0,dayAnchor-equity);dayPeakEquity=equity;dayPeakToTrough=0;
  Event("prague_day_start","Anchor reconstructed from all same-day deal cash, including costs");
 }
 dayMinimum=MathMin(dayMinimum,equity);dayMaxLoss=MathMax(dayMaxLoss,dayAnchor-equity);
 dayPeakEquity=MathMax(dayPeakEquity,equity);dayPeakToTrough=MathMax(dayPeakToTrough,dayPeakEquity-equity);
 overallPeak=MathMax(overallPeak,equity);observedDDCash=MathMax(observedDDCash,overallPeak-equity);
 observedDDPct=MathMax(observedDDPct,100*(overallPeak-equity)/overallPeak);
 maximumPositions=MathMax(maximumPositions,PositionsTotal());maxMarginProxy=MathMax(maxMarginProxy,MarginProxy());
 if(officialStatus==0)
 {
  if(equity<9000.0-1e-7)officialStatus=-2;
  else if(equity<dayAnchor-500.0-1e-7)officialStatus=-1;
  else if(permitPass && PositionsTotal()==0 && OrdersTotal()==0 && ArraySize(entryDays)>=4 && AccountInfoDouble(ACCOUNT_BALANCE)>=(InpPhase==1?11000.0:10500.0)-1e-7)officialStatus=1;
  if(officialStatus!=0)
  {
   statusEpoch=now;statusEquity=equity;statusBalance=AccountInfoDouble(ACCOUNT_BALANCE);statusAnchor=dayAnchor;
   Event(officialStatus==1?"natural_phase_pass":"permanent_phase_failure","First terminal FTMO-rule status; no target liquidation");
  }
 }
 if(now/60!=lastMinute/60)
 {
  lastMinute=now;
  FileWrite(auditFile,(long)now,PragueDay(now),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(equity,2),DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN),2),DoubleToString(MarginProxy(),2),DoubleToString(dayAnchor,2),DoubleToString(dayMaxLoss,2),PositionsTotal(),officialStatus);
 }
}
void LiquidateFailure()
{
 if(!InpChallenge || officialStatus>=0 || liquidating)return;
 liquidating=true;CTrade closeTrade;closeTrade.SetDeviationInPoints(1000);
 for(int i=OrdersTotal()-1;i>=0;i--){ulong ticket=OrderGetTicket(i);if(ticket>0)closeTrade.OrderDelete(ticket);}
 for(int i=PositionsTotal()-1;i>=0;i--){ulong ticket=PositionGetTicket(i);if(ticket>0){closeTrade.SetTypeFillingBySymbol(PositionGetString(POSITION_SYMBOL));closeTrade.PositionClose(ticket,1000);}}
 liquidating=false;
}
bool PortfolioOrderSend(const MqlTradeRequest &request,MqlTradeResult &result)
{
 if(!MQLInfoInteger(MQL_TESTER)){ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;return false;}
 bool entry=(request.action==TRADE_ACTION_DEAL && request.position==0) || request.action==TRADE_ACTION_PENDING;
 if(!entry)return OrderSend(request,result); // Exits and stop management are never suppressed.
 Observe();double equity=AccountInfoDouble(ACCOUNT_EQUITY),existing=MarginProxy();
 MqlTick tick={};bool quote=SymbolInfoTick(request.symbol,tick);
 bool buy=request.type==ORDER_TYPE_BUY || request.type==ORDER_TYPE_BUY_STOP || request.type==ORDER_TYPE_BUY_LIMIT;
 double price=request.price>0?request.price:(buy?tick.ask:tick.bid);
 double need=request.volume*SymbolInfoDouble(request.symbol,SYMBOL_TRADE_CONTRACT_SIZE)*MathMax(price,MathMax(tick.ask,tick.bid))/15.0;
 double planned=0,unit=0,brokerNeed=0;bool calculated=OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,request.symbol,request.volume,price,request.sl,unit);
 bool marginCalculated=OrderCalcMargin(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,request.symbol,request.volume,price,brokerNeed);
 if(calculated)planned=MathMax(0,-unit);
 string reason="admitted";
 if((InpChallenge && officialStatus!=0) || (InpTradingFromEpoch>0 && TimeCurrent()<InpTradingFromEpoch))reason="phase_inactive";
 else if(!quote || tick.ask<=0 || tick.bid<=0 || !MathIsValidNumber(need))reason="invalid_quote_or_notional";
 else if(existing+need>equity+1e-7)reason="gross_notional_15_margin";
 FileWrite(admitFile,(long)TimeCurrent(),request.magic,request.symbol,(int)request.type,DoubleToString(equity,2),DoubleToString(equity*.01,6),DoubleToString(request.volume,8),DoubleToString(price,8),DoubleToString(request.sl,8),DoubleToString(request.tp,8),DoubleToString(planned,6),DoubleToString(existing,6),DoubleToString(need,6),DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE),6),reason,DoubleToString(tick.bid,8),DoubleToString(tick.ask,8),DoubleToString(SymbolInfoDouble(request.symbol,SYMBOL_TRADE_CONTRACT_SIZE),8),marginCalculated,DoubleToString(brokerNeed,8));
 if(reason!="admitted"){ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;result.comment=reason;Event("entry_rejected",reason);return false;}
 bool sent=OrderSend(request,result);Observe();RefreshLedger(true);Observe();return sent;
}
bool Fresh(const string symbol,long &seen)
{
 MqlTick tick={};if(!SymbolInfoTick(symbol,tick)||tick.time_msc==seen||tick.bid<=0||tick.ask<=0)return false;
 seen=tick.time_msc;return true;
}
void ExportContracts()
{
 string names[2]={"USTEC","XAUUSD"};
 for(int i=0;i<2;i++)
 {
  string s=names[i];double im=0,mm=0;SymbolInfoMarginRate(s,ORDER_TYPE_BUY,im,mm);
  FileWrite(contractFile,s,(int)SymbolInfoInteger(s,SYMBOL_DIGITS),SymbolInfoDouble(s,SYMBOL_POINT),SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(s,SYMBOL_TRADE_TICK_VALUE_PROFIT),SymbolInfoDouble(s,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(s,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(s,SYMBOL_VOLUME_MIN),SymbolInfoDouble(s,SYMBOL_VOLUME_STEP),SymbolInfoDouble(s,SYMBOL_VOLUME_MAX),(int)SymbolInfoInteger(s,SYMBOL_TRADE_CALC_MODE),SymbolInfoString(s,SYMBOL_CURRENCY_PROFIT),im,mm,AccountInfoInteger(ACCOUNT_LEVERAGE));
 }
}
bool OpenAudit()
{
 auditFile=FileOpen(AuditPath("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 eventFile=FileOpen(AuditPath("events"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 admitFile=FileOpen(AuditPath("admissions"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 dayFile=FileOpen(AuditPath("days"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 contractFile=FileOpen(AuditPath("contracts"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(auditFile==INVALID_HANDLE || eventFile==INVALID_HANDLE || admitFile==INVALID_HANDLE || dayFile==INVALID_HANDLE || contractFile==INVALID_HANDLE)return false;
 FileWrite(auditFile,"epoch","prague_day","balance","equity","broker_margin","gross_notional_margin15","day_start_balance","max_daily_equity_loss","positions","status");
 FileWrite(eventFile,"epoch","prague_day","kind","status","balance","equity","day_start_balance","entry_days","positions","orders","info");
 FileWrite(admitFile,"epoch","magic","symbol","type","equity","nominal_budget","lots","requested_entry","sl","tp","planned_stop_risk","existing_margin15","new_margin15","broker_free_margin","decision","bid","ask","contract_size","broker_margin_calculated","broker_proposed_margin");
 FileWrite(dayFile,"prague_day","day_start_balance","minimum_observed_equity","max_equity_loss_from_day_start","equity_peak_to_trough","daily_equity_floor");
 FileWrite(contractFile,"symbol","digits","point","tick_size","tick_value_profit","tick_value_loss","contract_size","volume_min","volume_step","volume_max","calc_mode","profit_currency","initial_margin_rate","maintenance_margin_rate","account_leverage");
 ExportContracts();return true;
}
void ExportDeals()
{
 if(!HistorySelect(0,TimeCurrent()+86400)){Print("FTMO3_EXPORT_FAILED");return;}
 int f=FileOpen(AuditPath("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","order","magic","sl","tp","reason","comment","order_price_open","order_type","time_msc","symbol");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;ulong o=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
  FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),type,DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),o,HistoryDealGetInteger(d,DEAL_MAGIC),DoubleToString(HistoryOrderGetDouble(o,ORDER_SL),8),DoubleToString(HistoryOrderGetDouble(o,ORDER_TP),8),HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetString(d,DEAL_COMMENT),DoubleToString(HistoryOrderGetDouble(o,ORDER_PRICE_OPEN),8),HistoryOrderGetInteger(o,ORDER_TYPE),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetString(d,DEAL_SYMBOL));
 }
 FileClose(f);
}
void FinishAudit()
{
 // Never evaluate pass/fail after native end-of-test liquidation.
 ExportDeals();WriteDay();
 int f=FileOpen(AuditPath("status"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"status","status_epoch","status_balance","status_equity","status_day_start_balance","entry_days","first_observed","last_observed","observed_equity_dd_cash","observed_equity_dd_pct","max_positions","max_margin15","balance_after_tester_close");
 FileWrite(f,officialStatus,(long)statusEpoch,statusBalance,statusEquity,statusAnchor,ArraySize(entryDays),(long)firstObserved,(long)lastObserved,observedDDCash,observedDDPct,maximumPositions,maxMarginProxy,AccountInfoDouble(ACCOUNT_BALANCE));FileClose(f);
 Print("FTMO3_COMPLETE tag=",InpTag," status=",officialStatus," first=",(long)firstObserved," last=",(long)lastObserved," balance=",AccountInfoDouble(ACCOUNT_BALANCE)," observed_daily_monitoring=primary_ticks_plus_1s_timer");
}

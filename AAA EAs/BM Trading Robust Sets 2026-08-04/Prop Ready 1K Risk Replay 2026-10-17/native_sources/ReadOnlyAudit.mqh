// Tester-only observational instrumentation. No orders or account changes.
input string InpRR05AuditTag="";
int rr05_equity_file=INVALID_HANDLE;
int rr05_risk_file=INVALID_HANDLE;
datetime rr05_last_trace=0;
string RR05Path(const string suffix){return "CalyxRR05All20261008\\"+InpRR05AuditTag+"-"+suffix+".csv";}
bool RR05AuditInit()
{
 if(!MQLInfoInteger(MQL_TESTER) || InpRR05AuditTag=="")return false;
 FolderCreate("CalyxRR05All20261008",FILE_COMMON);
 rr05_equity_file=FileOpen(RR05Path("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(rr05_equity_file==INVALID_HANDLE)return false;
 FileWrite(rr05_equity_file,"epoch","balance","equity");
 rr05_risk_file=FileOpen(RR05Path("entry_risk"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(rr05_risk_file==INVALID_HANDLE)return false;
 FileWrite(rr05_risk_file,"position_id","deal","epoch","symbol","side","entry_price","sl","sl_source","unit_risk","calculation_ok","quote_bid","quote_ask","quote_epoch","source_volume","open_swap","margin_one_lot","margin_ok");
 return true;
}
// Observes deal-add notifications only. Original sources have no transaction
// callback; no order placement, rule alteration or timing wait is introduced.
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(!MQLInfoInteger(MQL_TESTER) || rr05_risk_file==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)return;
 if(!HistoryDealSelect(trans.deal))return;
 long entry=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
 long kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE);
 if(entry!=DEAL_ENTRY_IN || (kind!=DEAL_TYPE_BUY && kind!=DEAL_TYPE_SELL))return;
 long pid=HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
 datetime when=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
 string symbol=HistoryDealGetString(trans.deal,DEAL_SYMBOL);
 double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE),volume=HistoryDealGetDouble(trans.deal,DEAL_VOLUME);
 ulong order=(ulong)HistoryDealGetInteger(trans.deal,DEAL_ORDER);
 double sl=0,swap=0;string source="unavailable";
 if(HistoryOrderSelect(order)){sl=HistoryOrderGetDouble(order,ORDER_SL);if(sl>0)source="entry_order";}
 if(PositionSelectByTicket(trans.position)){
   swap=PositionGetDouble(POSITION_SWAP);
   if(sl<=0){sl=PositionGetDouble(POSITION_SL);if(sl>0)source="live_position_at_deal_callback";}
 }
 MqlTick tick={};SymbolInfoTick(symbol,tick);
 ENUM_ORDER_TYPE side=kind==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double profit=0,margin=0;
 bool ok=sl>0 && OrderCalcProfit(side,symbol,1,price,sl,profit) && profit<0;
 bool margin_ok=OrderCalcMargin(side,symbol,1,price,margin);
 FileWrite(rr05_risk_file,pid,trans.deal,(long)when,symbol,(int)side,DoubleToString(price,8),DoubleToString(sl,8),source,
   DoubleToString(-profit,10),ok?1:0,DoubleToString(tick.bid,8),DoubleToString(tick.ask,8),(long)tick.time,
   DoubleToString(volume,8),DoubleToString(swap,8),DoubleToString(margin,10),margin_ok?1:0);
}
void RR05Observe()
{
 if(rr05_equity_file==INVALID_HANDLE)return;
 datetime now=TimeCurrent();
 if(rr05_last_trace>0 && now/300==rr05_last_trace/300)return;
 rr05_last_trace=now;
 FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
}
void RR05Finish()
{
 if(rr05_equity_file==INVALID_HANDLE)return;
 FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
 FileClose(rr05_equity_file);rr05_equity_file=INVALID_HANDLE;
 if(rr05_risk_file!=INVALID_HANDLE){FileClose(rr05_risk_file);rr05_risk_file=INVALID_HANDLE;}
 int file=FileOpen(RR05Path("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(file==INVALID_HANDLE || !HistorySelect(0,TimeCurrent())){Print("RR05_EXPORT_FAILED");return;}
 FileWrite(file,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","order","magic","sl","tp","reason","comment","order_price_open","order_type","time_msc");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);
  long kind=HistoryDealGetInteger(d,DEAL_TYPE);
  if(kind!=DEAL_TYPE_BUY && kind!=DEAL_TYPE_SELL)continue;
  ulong order=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
  FileWrite(file,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),kind,
    DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),
    DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),
    DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),
    order,HistoryDealGetInteger(d,DEAL_MAGIC),DoubleToString(HistoryOrderGetDouble(order,ORDER_SL),8),
    DoubleToString(HistoryOrderGetDouble(order,ORDER_TP),8),HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetString(d,DEAL_COMMENT),
    DoubleToString(HistoryOrderGetDouble(order,ORDER_PRICE_OPEN),8),HistoryOrderGetInteger(order,ORDER_TYPE),HistoryDealGetInteger(d,DEAL_TIME_MSC));
 }
 FileClose(file);
 file=FileOpen(RR05Path("coverage"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 MqlRates rates[];
 int count=CopyRates(_Symbol,PERIOD_M1,D'2026.08.17 00:00:00',D'2026.10.16 23:59:59',rates);
 if(file==INVALID_HANDLE || count<=0){Print("RR05_EXPORT_FAILED coverage");if(file!=INVALID_HANDLE)FileClose(file);return;}
 FileWrite(file,"symbol","m1_count","m1_first","m1_last","final_simulated_epoch");
 FileWrite(file,_Symbol,count,(long)rates[0].time,(long)rates[count-1].time,(long)TimeCurrent());
 FileClose(file);
 file=FileOpen(RR05Path("contracts"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(file==INVALID_HANDLE){Print("RR05_EXPORT_FAILED contracts");return;}
 double initial=0,maintenance=0,buy_margin=0,sell_margin=0;
 SymbolInfoMarginRate(_Symbol,ORDER_TYPE_BUY,initial,maintenance);
 MqlTick tick={};SymbolInfoTick(_Symbol,tick);
 bool buy_ok=OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,1,tick.ask,buy_margin);
 bool sell_ok=OrderCalcMargin(ORDER_TYPE_SELL,_Symbol,1,tick.bid,sell_margin);
 FileWrite(file,"symbol","digits","point","tick_size","tick_value_profit","tick_value_loss","contract_size","volume_min","volume_step","volume_max","calc_mode","profit_currency","initial_margin_rate","maintenance_margin_rate","account_leverage","buy_margin_one_lot","sell_margin_one_lot","margin_calc_ok");
 FileWrite(file,_Symbol,SymbolInfoInteger(_Symbol,SYMBOL_DIGITS),SymbolInfoDouble(_Symbol,SYMBOL_POINT),
   SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_PROFIT),
   SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),
   SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),
   SymbolInfoInteger(_Symbol,SYMBOL_TRADE_CALC_MODE),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT),initial,maintenance,
   AccountInfoInteger(ACCOUNT_LEVERAGE),buy_margin,sell_margin,(buy_ok&&sell_ok)?1:0);
 FileClose(file);
 Print("RR05_EXPORT_COMPLETE");
}

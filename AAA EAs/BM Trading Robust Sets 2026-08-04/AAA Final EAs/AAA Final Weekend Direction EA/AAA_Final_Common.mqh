#ifndef AAA_FINAL_COMMON_MQH
#define AAA_FINAL_COMMON_MQH

#include <Trade/Trade.mqh>

CTrade AAA_Trade;
int AAA_TesterServerOffsetMode=1; // 1 = EET/EEST broker clock, used only in the Strategy Tester

double AAA_Price(const string symbol,const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
}

double AAA_Volume(const string symbol,const double raw)
{
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double AAA_LotsForRisk(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double risk_percent)
{
   if(risk_percent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double loss=MathAbs(one_lot_result);
   if(loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*risk_percent/100.0;
   return AAA_Volume(symbol,risk_cash/loss);
}

bool AAA_HasPosition(const string symbol,const long magic)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==symbol && PositionGetInteger(POSITION_MAGIC)==magic) return true;
   }
   return false;
}

bool AAA_HasOrder(const string symbol,const long magic)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic) return true;
   }
   return false;
}

bool AAA_HasExposure(const string symbol,const long magic)
{
   return AAA_HasPosition(symbol,magic) || AAA_HasOrder(symbol,magic);
}

void AAA_DeleteOrders(const string symbol,const long magic)
{
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic)
         AAA_Trade.OrderDelete(ticket);
   }
}

bool AAA_NewBar(const string symbol,const ENUM_TIMEFRAMES timeframe,datetime &last_bar)
{
   datetime current=iTime(symbol,timeframe,0);
   if(current<=0 || current==last_bar) return false;
   last_bar=current;
   return true;
}

double AAA_BufferValue(const int handle,const int buffer,const int shift)
{
   if(handle==INVALID_HANDLE) return EMPTY_VALUE;
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,buffer,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

double AAA_ATR(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iATR(symbol,timeframe,period);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_MA(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift,const ENUM_MA_METHOD method=MODE_EMA)
{
   int handle=iMA(symbol,timeframe,period,0,method,PRICE_CLOSE);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_RSI(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iRSI(symbol,timeframe,period,PRICE_CLOSE);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_ADX(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iADX(symbol,timeframe,period);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

int AAA_DaysInMonth(const int year,const int month)
{
   if(month==2) return ((year%4==0 && year%100!=0) || year%400==0 ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int AAA_LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=AAA_DaysInMonth(year,month); p.hour=12;
   datetime stamp=StructToTime(p);
   TimeToStruct(stamp,p);
   return AAA_DaysInMonth(year,month)-p.day_of_week;
}

int AAA_TesterEETOffsetSeconds(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(server_time,p);
   bool summer=false;
   if(p.mon>3 && p.mon<10) summer=true;
   else if(p.mon==3)
   {
      int last=AAA_LastSunday(p.year,3);
      summer=(p.day>last || (p.day==last && p.hour>=3));
   }
   else if(p.mon==10)
   {
      int last=AAA_LastSunday(p.year,10);
      summer=(p.day<last || (p.day==last && p.hour<4));
   }
   return (summer ? 3 : 2)*3600;
}

int AAA_ServerOffsetSeconds()
{
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   // In MT5 tests TimeGMT() is simulated as server time. Rebuild the active
   // broker's EET/EEST offset so UTC and New York session rules remain testable.
   if((bool)MQLInfoInteger(MQL_TESTER) && AAA_TesterServerOffsetMode==1)
      return AAA_TesterEETOffsetSeconds(server);
   return (int)(server-TimeGMT());
}

datetime AAA_ToUTC(const datetime server_time)
{
   return server_time-AAA_ServerOffsetSeconds();
}

datetime AAA_ToServer(const datetime utc_time)
{
   return utc_time+AAA_ServerOffsetSeconds();
}

int AAA_UTCDateKey(const datetime server_time)
{
   MqlDateTime part;
   TimeToStruct(AAA_ToUTC(server_time),part);
   return part.year*10000+part.mon*100+part.day;
}

datetime AAA_UTCDateTime(const datetime server_time,const int hour,const int minute=0)
{
   MqlDateTime part;
   TimeToStruct(AAA_ToUTC(server_time),part);
   part.hour=hour;
   part.min=minute;
   part.sec=0;
   return AAA_ToServer(StructToTime(part));
}

int AAA_NewYorkOffsetHours(const datetime utc_time)
{
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   // Sufficient deterministic DST approximation for trading-window selection.
   if(p.mon>3 && p.mon<11) return -4;
   if(p.mon<3 || p.mon>11) return -5;
   if(p.mon==3 && p.day>=8) return -4;
   if(p.mon==11 && p.day<8) return -4;
   return -5;
}

datetime AAA_ToNewYork(const datetime server_time)
{
   datetime utc=AAA_ToUTC(server_time);
   return utc+AAA_NewYorkOffsetHours(utc)*3600;
}

datetime AAA_NewYorkToServer(const datetime ny_time)
{
   MqlDateTime p;
   TimeToStruct(ny_time,p);
   // Resolve using the same calendar day; the DST approximation above is stable around session hours.
   datetime guessed_utc=ny_time+5*3600;
   int offset=AAA_NewYorkOffsetHours(guessed_utc);
   return AAA_ToServer(ny_time-offset*3600);
}

bool AAA_SessionRangeUTC(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now=TimeCurrent();
   datetime from=AAA_UTCDateTime(now,start_hour);
   datetime to=AAA_UTCDateTime(now,end_hour)-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX;
   low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool AAA_SessionRangeNY(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now_ny=AAA_ToNewYork(TimeCurrent());
   MqlDateTime p;
   TimeToStruct(now_ny,p);
   p.hour=start_hour; p.min=0; p.sec=0;
   datetime from=AAA_NewYorkToServer(StructToTime(p));
   p.hour=end_hour;
   datetime to=AAA_NewYorkToServer(StructToTime(p))-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX; low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool AAA_TradedToday(const string symbol,const long magic)
{
   datetime start=AAA_UTCDateTime(TimeCurrent(),0);
   if(!HistorySelect(start,TimeCurrent())) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)==symbol && HistoryDealGetInteger(ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN) return true;
   }
   return false;
}

bool AAA_SendMarket(const string symbol,const int direction,const double stop,const double reward_risk,const double risk_percent,const long magic,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=AAA_Price(symbol,stop);
   if((direction>0 && sl>=entry) || (direction<0 && sl<=entry)) return false;
   double tp=AAA_Price(symbol,entry+direction*MathAbs(entry-sl)*reward_risk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=AAA_LotsForRisk(symbol,type,entry,sl,risk_percent);
   if(lots<=0.0)
   {
      Print(comment,": size below broker minimum or contract data unavailable");
      return false;
   }
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   AAA_Trade.SetTypeFillingBySymbol(symbol);
   AAA_Trade.SetDeviationInPoints(20);
   if(direction>0) return AAA_Trade.Buy(lots,symbol,0.0,sl,tp,comment);
   return AAA_Trade.Sell(lots,symbol,0.0,sl,tp,comment);
}

bool AAA_SendPending(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double reward_risk,const double risk_percent,const long magic,const datetime expiry,const string comment)
{
   int direction=(type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_BUY_LIMIT ? 1 : -1);
   double price=AAA_Price(symbol,entry);
   double sl=AAA_Price(symbol,stop);
   if((direction>0 && sl>=price) || (direction<0 && sl<=price)) return false;
   double tp=AAA_Price(symbol,price+direction*MathAbs(price-sl)*reward_risk);
   double lots=AAA_LotsForRisk(symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),price,sl,risk_percent);
   if(lots<=0.0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   AAA_Trade.SetTypeFillingBySymbol(symbol);
   if(type==ORDER_TYPE_BUY_STOP) return AAA_Trade.BuyStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_STOP) return AAA_Trade.SellStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_BUY_LIMIT) return AAA_Trade.BuyLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_LIMIT) return AAA_Trade.SellLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   return false;
}

void AAA_ManageOCO(const string symbol,const long magic)
{
   if(AAA_HasPosition(symbol,magic)) AAA_DeleteOrders(symbol,magic);
}

void AAA_TrailR(const string symbol,const long magic,const double start_r,const double distance_r)
{
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return;
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double sl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      if(sl<=0.0 || tp<=0.0) continue;
      int direction=(type==POSITION_TYPE_BUY ? 1 : -1);
      double initial_r=MathAbs(tp-open);
      double rr=1.0;
      if(initial_r>0.0) rr=MathMax(0.1,initial_r/MathMax(MathAbs(open-sl),SymbolInfoDouble(symbol,SYMBOL_POINT)));
      initial_r=initial_r/rr;
      double price=(direction>0 ? tick.bid : tick.ask);
      if(direction*(price-open)<start_r*initial_r) continue;
      double candidate=AAA_Price(symbol,price-direction*distance_r*initial_r);
      if((direction>0 && candidate>sl && candidate<price) || (direction<0 && (sl==0.0 || candidate<sl) && candidate>price))
         AAA_Trade.PositionModify(ticket,candidate,tp);
   }
}

#endif

#property copyright "Gold News V9"
#property version   "1.14"
#property strict
#property description "Consumes the local Gold News V9 API for NFP, CPI, and FOMC."

#include <Trade\Trade.mqh>
#include "..\..\AAA EAs\BM Trading Robust Sets 2026-08-04\_Shared\CalyxAdaptivePortfolio.mqh"

enum ENUM_GNV9_STATE
  {
   GNV9_IDLE=0,
   GNV9_SCHEDULED=1,
   GNV9_ARMED=2,
   GNV9_ENTRY_SENT=3,
   GNV9_POSITION_OPEN=4,
   GNV9_DONE=5,
   GNV9_SKIPPED=6
  };

input bool   InpEnableTrading=true;
input bool   InpRequireDemoAccount=false;
input bool   InpUseFileBridge=true;
input string InpApiBaseUrl="http://127.0.0.1:8799";
input int    InpHttpTimeoutMs=5000;
input int    InpCalendarPollSeconds=60;
input int    InpPredictionLeadMinutes=15;
input int    InpSignalPollSeconds=5;
input int    InpEntryLeadSeconds=10;
input int    InpExitAfterReleaseSeconds=900;
input double InpStopDistanceUSD=20.00;
input double InpTakeProfitDistanceUSD=4.00;
input double InpRiskPercent=0.75;
input bool   InpAdaptivePortfolioControls=false;
input double InpMaxLot=1.00;
input double InpMarginReservePercent=10.0;
input double InpMaxSpreadUSD=0.0;
input int    InpMaxSpreadPoints=0;
input int    InpMaxDeviationPoints=100;
input double InpMinimumConfidencePct=0.0;
input bool   InpTradeLowConfidence=true;
input bool   InpEnableNFP=true;
input bool   InpEnableCPI=true;
input bool   InpEnableFOMC=true;
input bool   InpCloseUnprotectedPosition=true;
input long   InpMagicNumber=90915001;
input int    InpTimerMilliseconds=250;

const string STATE_FILE="GoldNewsV9EA\\state.tsv";
const string BRIDGE_FILE="GoldNewsV9EA\\bridge.json";
const string RUNTIME_FILE="GoldNewsV9EA\\runtime.tsv";
const int MIN_PREDICTION_LEAD_SECONDS=480;
const int MAX_PREDICTION_LEAD_SECONDS=1800;
const int SYMBOL_SYNC_RETRY_SECONDS=5;

CTrade trade;
ENUM_GNV9_STATE state=GNV9_IDLE;
string trade_symbol="";
string event_name="";
string release_iso="";
datetime release_utc=0;
string event_forecast="";
string event_previous="";
string signal_direction="";
string signal_tier="";
double signal_confidence=0.0;
ulong position_ticket=0;
datetime last_calendar_poll=0;
datetime last_signal_poll=0;
datetime last_symbol_sync_attempt=0;
datetime last_runtime_write=0;
string last_status="Starting";
string last_printed_status="";
datetime last_status_print=0;
const int REPEATED_STATUS_LOG_SECONDS=900;

string Upper(string value)
  {
   StringToUpper(value);
   return value;
  }

string CompactSymbol(string value)
  {
   value=Upper(value);
   string result="";
   for(int i=0;i<StringLen(value);i++)
     {
      ushort c=(ushort)StringGetCharacter(value,i);
      if((c>='A' && c<='Z') || (c>='0' && c<='9'))
         result+=StringSubstr(value,i,1);
     }
   return result;
  }

bool IsGoldSymbol(string name)
  {
   string compact=CompactSymbol(name);
   return StringFind(compact,"XAUUSD")==0 || compact=="GOLD";
  }

int GoldSymbolScore(string name)
  {
   string compact=CompactSymbol(name);
   if(compact=="XAUUSD")
      return 0;
   if(StringFind(compact,"XAUUSD")==0)
      return 10+StringLen(compact);
   if(compact=="GOLD")
      return 30;
   if(StringFind(compact,"GOLD")==0)
      return 40+StringLen(compact);
   return 100000;
  }

string ResolveGoldSymbol()
  {
   if(IsGoldSymbol(_Symbol) && SymbolSelect(_Symbol,true))
      return _Symbol;
   if(SymbolSelect("XAUUSD",true))
      return "XAUUSD";

   string best="";
   int best_score=100000;
   int total=SymbolsTotal(false);
   for(int i=0;i<total;i++)
     {
      string name=SymbolName(i,false);
      int score=GoldSymbolScore(name);
      if(score<best_score && SymbolSelect(name,true))
        {
         best=name;
         best_score=score;
        }
     }
   return best;
  }

bool IsSupportedEvent(string name)
  {
   name=Upper(name);
   if(name=="NFP")
      return InpEnableNFP;
   if(name=="CPI")
      return InpEnableCPI;
   if(name=="FOMC")
      return InpEnableFOMC;
   return false;
  }

string Trim(string value)
  {
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
  }

string JsonValue(string json,string key)
  {
   string token="\""+key+"\"";
   int pos=StringFind(json,token);
   if(pos<0)
      return "";
   pos=StringFind(json,":",pos+StringLen(token));
   if(pos<0)
      return "";
   pos++;
   while(pos<StringLen(json))
     {
      string ch=StringSubstr(json,pos,1);
      if(ch!=" " && ch!="\r" && ch!="\n" && ch!="\t")
         break;
      pos++;
     }
   if(pos>=StringLen(json))
      return "";
   if(StringSubstr(json,pos,1)=="\"")
     {
      pos++;
      string result="";
      bool escaped=false;
      for(int i=pos;i<StringLen(json);i++)
        {
         string ch=StringSubstr(json,i,1);
         if(escaped)
           {
            if(ch=="n")
               result+="\n";
            else
               result+=ch;
            escaped=false;
            continue;
           }
         if(ch=="\\")
           {
            escaped=true;
            continue;
           }
         if(ch=="\"")
            return result;
         result+=ch;
        }
      return "";
     }
   int end=pos;
   while(end<StringLen(json))
     {
      string ch=StringSubstr(json,end,1);
      if(ch=="," || ch=="}" || ch=="\r" || ch=="\n")
         break;
      end++;
     }
   return Trim(StringSubstr(json,pos,end-pos));
  }

string UrlEncode(string value)
  {
   string encoded="";
   for(int i=0;i<StringLen(value);i++)
     {
      int c=(int)StringGetCharacter(value,i);
      bool safe=(c>='A' && c<='Z') || (c>='a' && c<='z') ||
                (c>='0' && c<='9') || c=='-' || c=='_' || c=='.' || c=='~';
      if(safe)
         encoded+=StringSubstr(value,i,1);
      else
         encoded+=StringFormat("%%%02X",c);
     }
   return encoded;
  }

datetime ParseUtcIso(string value)
  {
   if(StringLen(value)<19)
      return 0;
   string core=StringSubstr(value,0,19);
   StringReplace(core,"T"," ");
   StringReplace(core,"-",".");
   return StringToTime(core);
  }

string StateName()
  {
   switch(state)
     {
      case GNV9_IDLE: return "IDLE";
      case GNV9_SCHEDULED: return "SCHEDULED";
      case GNV9_ARMED: return "ARMED";
      case GNV9_ENTRY_SENT: return "ENTRY_SENT";
      case GNV9_POSITION_OPEN: return "POSITION_OPEN";
      case GNV9_DONE: return "DONE";
      case GNV9_SKIPPED: return "SKIPPED";
     }
   return "UNKNOWN";
  }

void SetStatus(string text)
  {
   last_status=text;
   datetime now=TimeLocal();
   if(text!=last_printed_status || last_status_print==0 || now-last_status_print>=REPEATED_STATUS_LOG_SECONDS)
     {
      Print("Gold News V9: ",text);
      last_printed_status=text;
      last_status_print=now;
     }
  }

void SaveRuntimeHeartbeat()
  {
   datetime now=TimeGMT();
   if(last_runtime_write>0 && now-last_runtime_write<5)
      return;
   last_runtime_write=now;
   FolderCreate("GoldNewsV9EA",FILE_COMMON);
   int handle=FileOpen(
      RUNTIME_FILE,
      FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,
      '\t'
   );
   if(handle==INVALID_HANDLE)
      return;
   FileWrite(
      handle,
      (long)now,
      StateName(),
      trade_symbol,
      last_status
   );
   FileClose(handle);
  }

bool EnsureTradeSymbolReady()
  {
   MqlTick tick;
   if(trade_symbol!="" &&
      SymbolIsSynchronized(trade_symbol) &&
      SymbolInfoTick(trade_symbol,tick) &&
      tick.ask>0 && tick.bid>0)
     {
      trade.SetTypeFillingBySymbol(trade_symbol);
      return true;
     }

   datetime now=TimeGMT();
   if(last_symbol_sync_attempt>0 &&
      now-last_symbol_sync_attempt<SYMBOL_SYNC_RETRY_SECONDS)
      return false;
   last_symbol_sync_attempt=now;

   string resolved=ResolveGoldSymbol();
   if(resolved=="" ||
      !SymbolIsSynchronized(resolved) ||
      !SymbolInfoTick(resolved,tick) ||
      tick.ask<=0 || tick.bid<=0)
     {
      SetStatus("Waiting for the broker gold symbol to synchronize.");
      return false;
     }
   trade_symbol=resolved;
   trade.SetTypeFillingBySymbol(trade_symbol);
   SetStatus("Broker gold symbol synchronized: "+trade_symbol+".");
   return true;
  }

void SaveState()
  {
   FolderCreate("GoldNewsV9EA",FILE_COMMON);
   int handle=FileOpen(
      STATE_FILE,
      FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,
      '\t'
   );
   if(handle==INVALID_HANDLE)
     {
      Print("Gold News V9: state save failed, error ",GetLastError());
      return;
     }
   FileWrite(
      handle,
      (int)state,
      event_name,
      release_iso,
      (long)release_utc,
      event_forecast,
      event_previous,
      signal_direction,
      signal_tier,
      DoubleToString(signal_confidence,2),
      (long)position_ticket
   );
   FileClose(handle);
  }

void LoadState()
  {
   if(!FileIsExist(STATE_FILE,FILE_COMMON))
      return;
   int handle=FileOpen(
      STATE_FILE,
      FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,
      '\t'
   );
   if(handle==INVALID_HANDLE)
      return;
   state=(ENUM_GNV9_STATE)(int)FileReadNumber(handle);
   event_name=FileReadString(handle);
   release_iso=FileReadString(handle);
   release_utc=(datetime)(long)FileReadNumber(handle);
   event_forecast=FileReadString(handle);
   event_previous=FileReadString(handle);
   signal_direction=FileReadString(handle);
   signal_tier=FileReadString(handle);
   signal_confidence=FileReadNumber(handle);
   position_ticket=(ulong)(long)FileReadNumber(handle);
   FileClose(handle);
  }

void ResetEvent()
  {
   state=GNV9_IDLE;
   event_name="";
   release_iso="";
   release_utc=0;
   event_forecast="";
   event_previous="";
   signal_direction="";
   signal_tier="";
   signal_confidence=0.0;
   position_ticket=0;
   last_signal_poll=0;
   SaveState();
  }

bool ReadBridge(string &response)
  {
   ResetLastError();
   int handle=FileOpen(
      BRIDGE_FILE,
      FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE
   );
   if(handle==INVALID_HANDLE)
     {
      SetStatus("Waiting for local prediction bridge file.");
      return false;
     }
   response="";
   while(!FileIsEnding(handle))
      response+=FileReadString(handle);
   FileClose(handle);
   if(JsonValue(response,"bridge_status")!="OK")
     {
      SetStatus("Local prediction bridge is not ready.");
      return false;
     }
   long heartbeat=(long)StringToInteger(JsonValue(response,"heartbeat_epoch"));
   if(heartbeat<=0 || MathAbs((double)(TimeGMT()-heartbeat))>180.0)
     {
      SetStatus("Local prediction bridge heartbeat is stale.");
      return false;
     }
   return true;
  }

bool HttpRequest(
   string method,
   string endpoint,
   string body,
   string &response
)
  {
   string url=InpApiBaseUrl+endpoint;
   string headers="";
   char request[];
   char result[];
   string response_headers="";
   if(method=="POST")
     {
      headers="Content-Type: application/x-www-form-urlencoded\r\n";
      StringToCharArray(body,request,0,StringLen(body),CP_UTF8);
     }
   else
      ArrayResize(request,0);

   ResetLastError();
   int code=WebRequest(
      method,
      url,
      headers,
      InpHttpTimeoutMs,
      request,
      result,
      response_headers
   );
   if(code<0)
     {
      SetStatus(
         "WebRequest failed ("+IntegerToString(GetLastError())+
         "). Allow "+InpApiBaseUrl+" in MT5 Options."
      );
      return false;
     }
   response=CharArrayToString(result,0,ArraySize(result),CP_UTF8);
   if(code<200 || code>=300)
     {
      SetStatus(
         "API returned HTTP "+IntegerToString(code)+": "+
         StringSubstr(response,0,180)
      );
      return false;
     }
   return true;
  }

bool ApiHealthy()
  {
   string response="";
   if(!HttpRequest("GET","/api/health","",response))
      return false;
   return JsonValue(response,"status")=="ok" &&
          JsonValue(response,"gold_direction_v9_action_tier")=="true" &&
          JsonValue(response,"gold_move_range_v8")=="true";
  }

bool FetchNextEvent()
  {
   last_calendar_poll=TimeGMT();
   string response="";
   if(InpUseFileBridge)
     {
      if(!ReadBridge(response))
        {
         Print("Gold News V9: file bridge unavailable; trying HTTP calendar fallback.");
         if(!ApiHealthy() ||
            !HttpRequest("GET","/api/ea/next?days=30","",response))
            return false;
        }
     }
   else
     {
      if(!ApiHealthy())
         return false;
      if(!HttpRequest("GET","/api/ea/next?days=30","",response))
         return false;
     }
   if(JsonValue(response,"status")!="OK")
     {
      SetStatus("No supported NFP, CPI, or FOMC event found.");
      return false;
     }

   string next_event=Upper(JsonValue(response,"event"));
   string next_release=JsonValue(response,"release_utc");
   datetime parsed=ParseUtcIso(next_release);
   if(!IsSupportedEvent(next_event) || parsed<=TimeGMT())
     {
      SetStatus("Calendar response failed event or UTC validation.");
      return false;
     }

   event_name=next_event;
   release_iso=next_release;
   release_utc=parsed;
   event_forecast=JsonValue(response,"forecast");
   event_previous=JsonValue(response,"previous");
   state=GNV9_SCHEDULED;
   SaveState();
   SetStatus(
      "Scheduled "+event_name+" at "+
      TimeToString(release_utc,TIME_DATE|TIME_SECONDS)+" UTC."
   );
   return true;
  }

bool RequestSignal()
  {
   last_signal_poll=TimeGMT();
   string body=
      "event="+UrlEncode(event_name)+
      "&release="+UrlEncode(release_iso);
   if(event_forecast!="")
      body+="&forecast="+UrlEncode(event_forecast);
   if(event_previous!="")
      body+="&previous="+UrlEncode(event_previous);

   string response="";
   if(InpUseFileBridge)
     {
      bool bridge_ready=ReadBridge(response) &&
                        JsonValue(response,"signal_status")=="READY";
      if(!bridge_ready)
        {
         Print("Gold News V9: file signal unavailable; trying HTTP signal fallback.");
         if(!HttpRequest("POST","/api/ea/signal",body,response))
            return false;
        }
     }
   else if(!HttpRequest("POST","/api/ea/signal",body,response))
      return false;
   if(JsonValue(response,"status")!="OK")
     {
      SetStatus("Signal API did not return OK.");
      return false;
     }
   if(Upper(JsonValue(response,"event"))!=event_name ||
      ParseUtcIso(JsonValue(response,"release_utc"))!=release_utc)
     {
      SetStatus("Signal identity or UTC mismatch.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }
   if((int)StringToInteger(JsonValue(response,"artifact_version"))!=9)
     {
      SetStatus("Signal artifact version is not V9.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }

   signal_direction=Upper(JsonValue(response,"direction"));
   signal_tier=Upper(JsonValue(response,"action_tier"));
   signal_confidence=StringToDouble(JsonValue(response,"confidence_pct"));
   if(signal_direction!="POSITIVE" && signal_direction!="NEGATIVE")
     {
      SetStatus("Signal direction is invalid.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }
   if(signal_tier!="TRADE" && signal_tier!="LOW_CONFIDENCE")
     {
      SetStatus("Signal action tier is invalid.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }
   if(signal_tier=="LOW_CONFIDENCE" && !InpTradeLowConfidence)
     {
      SetStatus("Low-confidence event skipped by settings.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }
   if(signal_confidence<InpMinimumConfidencePct)
     {
      SetStatus("Signal confidence is below the configured minimum.");
      state=GNV9_SKIPPED;
      SaveState();
      return false;
     }

   state=GNV9_ARMED;
   SaveState();
   SetStatus(
      event_name+" armed "+signal_direction+" at "+
      DoubleToString(signal_confidence,2)+"%."
   );
   return true;
  }

double NormalizeVolume(double raw)
  {
   double step=SymbolInfoDouble(trade_symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(trade_symbol,SYMBOL_VOLUME_MIN);
   double maximum=MathMin(
      SymbolInfoDouble(trade_symbol,SYMBOL_VOLUME_MAX),
      InpMaxLot
   );
   if(step<=0.0)
      return 0.0;
   if(raw<=0.0 || minimum<=0.0 || maximum<=0.0)
      return 0.0;
   double volume=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   volume=MathMax(minimum,MathMin(volume,maximum));
   if(volume>raw+1e-12)
      PrintFormat("Gold News V9 risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw,volume);
   int digits=(int)MathMax(0,MathRound(-MathLog10(step)));
   return NormalizeDouble(volume,digits);
  }

bool FindOurPosition(ulong &ticket)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0)
         continue;
      if(PositionGetString(POSITION_SYMBOL)==trade_symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagicNumber)
        {
         ticket=candidate;
         return true;
        }
     }
   ticket=0;
   return false;
  }

bool TradingChecks(MqlTick &tick)
  {
   if(!EnsureTradeSymbolReady())
      return false;
   if(!InpEnableTrading)
     {
      SetStatus("Armed, but live trading is disabled in EA inputs.");
      return false;
     }
   if(InpRequireDemoAccount &&
      AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO)
     {
      SetStatus("Trading blocked because the account is not demo.");
      return false;
     }
   if(!TerminalInfoInteger(TERMINAL_CONNECTED) ||
      !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) ||
      !MQLInfoInteger(MQL_TRADE_ALLOWED) ||
      !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
     {
      SetStatus("Terminal or account trading permission is disabled.");
      return false;
     }
   if(!SymbolInfoTick(trade_symbol,tick) || tick.ask<=0 || tick.bid<=0)
     {
      SetStatus("No valid XAUUSD tick is available.");
      return false;
     }
   double spread=tick.ask-tick.bid;
   double point=SymbolInfoDouble(trade_symbol,SYMBOL_POINT);
   if(InpMaxSpreadUSD>0 && spread>InpMaxSpreadUSD)
     {
      SetStatus("Spread exceeds InpMaxSpreadUSD.");
      return false;
     }
   if(InpMaxSpreadPoints>0 && point>0 &&
      spread/point>InpMaxSpreadPoints)
     {
      SetStatus("Spread exceeds InpMaxSpreadPoints.");
      return false;
     }
   ulong existing=0;
   if(FindOurPosition(existing))
     {
      SetStatus("An EA-owned XAUUSD position already exists.");
      return false;
     }
   if(PositionSelect(trade_symbol))
     {
      SetStatus("An unrelated XAUUSD position exists; netting merge blocked.");
      return false;
     }
   return true;
  }

double RiskSizedLot(
   ENUM_ORDER_TYPE order_type,
   double entry,
   double stop,
   double &risk_budget,
   double &nominal_risk
)
  {
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagicNumber);
   if(adaptive<=0.0)
     {
      risk_budget=0.0;
      nominal_risk=0.0;
      return 0.0;
     }
   risk_budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent*adaptive/100.0;
   double one_lot_profit=0.0;
   if(!OrderCalcProfit(
      order_type,
      trade_symbol,
      1.0,
      entry,
      stop,
      one_lot_profit
   ))
      return 0.0;
   double one_lot_loss=MathAbs(one_lot_profit);
   if(one_lot_loss<=0)
      return 0.0;
   double lot=NormalizeVolume(risk_budget/one_lot_loss);
   nominal_risk=lot*one_lot_loss;
   return lot;
  }

bool OpenPredictedTrade()
  {
   MqlTick tick;
   if(!TradingChecks(tick))
      return false;
   bool is_buy=signal_direction=="POSITIVE";
   ENUM_ORDER_TYPE order_type=is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double entry=is_buy ? tick.ask : tick.bid;
   int digits=(int)SymbolInfoInteger(trade_symbol,SYMBOL_DIGITS);
   double stop=NormalizeDouble(
      is_buy ? entry-InpStopDistanceUSD : entry+InpStopDistanceUSD,
      digits
   );
   double target=0.0;
   if(InpTakeProfitDistanceUSD>0)
      target=NormalizeDouble(
         is_buy ? entry+InpTakeProfitDistanceUSD : entry-InpTakeProfitDistanceUSD,
         digits
      );
   double risk_budget=0.0;
   double nominal_risk=0.0;
   double lot=RiskSizedLot(
      order_type,entry,stop,risk_budget,nominal_risk
   );
   if(lot<=0)
     {
      SetStatus("Risk-based lot calculation failed.");
      return false;
     }
   if(nominal_risk>risk_budget+0.01)
      PrintFormat(
         "Gold News V9: actual risk %.2f exceeds selected risk %.2f because of broker minimum/step volume; trade remains enabled.",
         nominal_risk,
         risk_budget
      );

   double margin=0.0;
   if(!OrderCalcMargin(order_type,trade_symbol,lot,entry,margin))
     {
      SetStatus("OrderCalcMargin failed.");
      return false;
     }
   double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin>free_margin*(1.0-InpMarginReservePercent/100.0))
     {
      SetStatus("Insufficient free margin after reserve.");
      return false;
     }

   state=GNV9_ENTRY_SENT;
   SaveState();
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   trade.SetTypeFillingBySymbol(trade_symbol);
   string comment=
      "AI news "+event_name+(is_buy ? " buy " : " sell ")+
      DoubleToString(signal_confidence,1)+"%";
   bool sent=is_buy
      ? trade.Buy(lot,trade_symbol,0.0,stop,target,comment)
      : trade.Sell(lot,trade_symbol,0.0,stop,target,comment);
   if(!sent)
     {
      SetStatus(
         "Order rejected: "+IntegerToString((int)trade.ResultRetcode())+
         " "+trade.ResultRetcodeDescription()
      );
      state=GNV9_DONE;
      SaveState();
      return false;
     }

   if(!FindOurPosition(position_ticket))
     {
      SetStatus("Order accepted but no position was found; no retry.");
      state=GNV9_DONE;
      SaveState();
      return false;
     }
   if(!PositionSelectByTicket(position_ticket))
     {
      SetStatus("Filled position could not be selected.");
      state=GNV9_DONE;
      SaveState();
      return false;
     }
   double fill=PositionGetDouble(POSITION_PRICE_OPEN);
   double exact_stop=NormalizeDouble(
      is_buy ? fill-InpStopDistanceUSD : fill+InpStopDistanceUSD,
      digits
   );
   double exact_target=0.0;
   if(InpTakeProfitDistanceUSD>0)
      exact_target=NormalizeDouble(
         is_buy ? fill+InpTakeProfitDistanceUSD : fill-InpTakeProfitDistanceUSD,
         digits
      );
   if(!trade.PositionModify(position_ticket,exact_stop,exact_target))
     {
      SetStatus("Could not attach exact stop and target after fill.");
      if(InpCloseUnprotectedPosition)
         trade.PositionClose(position_ticket,InpMaxDeviationPoints);
      state=GNV9_DONE;
      SaveState();
      return false;
     }

   state=GNV9_POSITION_OPEN;
   SaveState();
   SetStatus(
      event_name+" position opened, lot "+DoubleToString(lot,2)+
      ", nominal risk $"+DoubleToString(nominal_risk,2)+
      ", TP $"+DoubleToString(InpTakeProfitDistanceUSD,2)+"."
   );
   return true;
  }

void ManagePosition()
  {
   ulong ticket=0;
   if(!FindOurPosition(ticket))
     {
      state=GNV9_DONE;
      position_ticket=0;
      SaveState();
      SetStatus(event_name+" position is closed.");
      return;
     }
   position_ticket=ticket;
   if(TimeGMT()<release_utc+InpExitAfterReleaseSeconds)
      return;
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(trade.PositionClose(position_ticket,InpMaxDeviationPoints))
     {
      state=GNV9_DONE;
      position_ticket=0;
      SaveState();
      SetStatus(
         event_name+" closed at T+"+
         IntegerToString(InpExitAfterReleaseSeconds)+" seconds."
      );
     }
   else
      SetStatus(
         "Time exit failed: "+IntegerToString((int)trade.ResultRetcode())+
         " "+trade.ResultRetcodeDescription()
      );
  }

void ReconcileState()
  {
   ulong ticket=0;
   if(FindOurPosition(ticket))
     {
      position_ticket=ticket;
      state=GNV9_POSITION_OPEN;
      SaveState();
      return;
     }
   if(state==GNV9_ENTRY_SENT)
     {
      state=GNV9_DONE;
      SaveState();
      SetStatus("Recovered ENTRY_SENT without a position; duplicate entry blocked.");
     }
  }

void RenderStatus()
  {
   string when=release_utc>0
      ? TimeToString(release_utc,TIME_DATE|TIME_SECONDS)+" UTC"
      : "-";
   Comment(
      "Gold News V9 EA\n",
      "Symbol: ",trade_symbol,"\n",
       "Server: ",InpApiBaseUrl,"\n",
       "Connection: ",InpUseFileBridge ? "LOCAL FILE BRIDGE" : "HTTP API","\n",
      "State: ",StateName(),"\n",
      "Event: ",event_name,"  ",when,"\n",
      "Signal: ",signal_direction,"  ",signal_tier,"  ",
      DoubleToString(signal_confidence,2),"%\n",
      "Live trading: ",InpEnableTrading ? "ENABLED" : "DISABLED","\n",
      "Status: ",last_status
   );
  }

int OnInit()
  {
   if(InpRiskPercent<=0 || InpRiskPercent>10 ||
       InpStopDistanceUSD<=0 ||
       InpTakeProfitDistanceUSD<0 ||
       InpPredictionLeadMinutes*60<MIN_PREDICTION_LEAD_SECONDS ||
       InpPredictionLeadMinutes*60>MAX_PREDICTION_LEAD_SECONDS)
     {
      Print("Gold News V9: invalid risk, stop, or prediction lead input.");
      return INIT_PARAMETERS_INCORRECT;
     }
   // Do not query broker symbol properties during initialization. MT5 can take
   // minutes to synchronize them after an account switch and remove the EA.
   trade_symbol=IsGoldSymbol(_Symbol) ? _Symbol : "";
   trade.SetExpertMagicNumber(InpMagicNumber);
   LoadState();
   ReconcileState();
   EventSetMillisecondTimer(MathMax(100,InpTimerMilliseconds));
   SetStatus("Initialized; broker symbol synchronization runs in the background.");
   SaveRuntimeHeartbeat();
   RenderStatus();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   SaveState();
   SaveRuntimeHeartbeat();
   EventKillTimer();
   Comment("");
  }

void OnTimer()
  {
   datetime now=TimeGMT();
   EnsureTradeSymbolReady();
   if(state==GNV9_POSITION_OPEN)
      ManagePosition();

   if((state==GNV9_DONE || state==GNV9_SKIPPED) &&
      release_utc>0 &&
      now>release_utc+InpExitAfterReleaseSeconds+60)
     {
      ResetEvent();
      last_calendar_poll=0;
     }

   if(state==GNV9_IDLE &&
      (last_calendar_poll==0 ||
       now-last_calendar_poll>=InpCalendarPollSeconds))
      FetchNextEvent();

   if(state==GNV9_SCHEDULED)
     {
       long seconds_to_release=(long)(release_utc-now);
       if(seconds_to_release<=InpPredictionLeadMinutes*60 &&
          seconds_to_release>=MIN_PREDICTION_LEAD_SECONDS &&
          (last_signal_poll==0 || now-last_signal_poll>=InpSignalPollSeconds))
          RequestSignal();
      else if(seconds_to_release<MIN_PREDICTION_LEAD_SECONDS)
        {
         state=GNV9_SKIPPED;
         SaveState();
         SetStatus("Prediction window was missed; event skipped.");
        }
     }

   if(state==GNV9_ARMED)
     {
      long seconds_to_release=(long)(release_utc-now);
      if(seconds_to_release<=InpEntryLeadSeconds &&
         seconds_to_release>0)
        {
         if(!OpenPredictedTrade() && state==GNV9_ARMED)
           {
            state=GNV9_SKIPPED;
            SaveState();
           }
        }
      else if(seconds_to_release<=0)
        {
         state=GNV9_SKIPPED;
         SaveState();
         SetStatus("Entry time was missed; no post-release chase.");
        }
     }
   SaveRuntimeHeartbeat();
   RenderStatus();
  }

void OnTradeTransaction(
   const MqlTradeTransaction &trans,
   const MqlTradeRequest &request,
   const MqlTradeResult &result
)
  {
   if(state==GNV9_ENTRY_SENT || state==GNV9_POSITION_OPEN)
      ReconcileState();
  }

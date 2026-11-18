//+------------------------------------------------------------------+
//| Calyx News Guard (2026-11-18)                                    |
//| Owner: "respect all the trading rules".                          |
//| FTMO funded Standard: no execution (entry, TP, SL, pending) 2 min |
//| before / after selected news on the affected instruments; The5ers|
//| High Stakes: no trades 2 min around high-impact news; FundingPips |
//| Master: 5 min (profit removed).                                  |
//|                                                                  |
//| One helper chart. For every listed release (Common\Files\        |
//| CalyxNewsCalendar.csv, written by Update News Calendar.bat):     |
//|  - from (release - before - lead) it blocks new EA entries on    |
//|    every symbol whose base or profit currency is the release     |
//|    currency (terminal global variable CNB_<symbol> = block end;  |
//|    the Calyx EAs refuse entries while it is set, input           |
//|    InpCalyxNewsBlock);                                           |
//|  - in the lead time before the window it CLOSES those symbols'   |
//|    EA positions and DELETES their EA pending orders, so no SL /  |
//|    TP / pending fill can execute inside the window;              |
//|  - the block ends at release + after.                            |
//| Manual trades (magic 0) are never touched unless asked. It never |
//| opens trades (except InpTestOpen in the tester).                 |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Calyx News Guard: closes EA trades and blocks EA entries around listed high-impact news (calendar file in Common\\Files)."
#include <Trade/Trade.mqh>

input bool   InpEnabled=true;
input int    InpBeforeMinutes=5;        // window starts this many minutes before the release (FTMO / The5ers 2, FundingPips 5)
input int    InpAfterMinutes=5;         // window ends this many minutes after the release
input int    InpCloseLeadSeconds=90;    // close positions / delete pending orders this many seconds BEFORE the window starts
input string InpImpacts="High";         // impacts to act on, comma list (High / Medium / Low)
input string InpCalendarFile="CalyxNewsCalendar.csv"; // Common\Files: utc_epoch,currency,impact,title
input int    InpStaleHours=36;          // warn if the file was fetched longer ago than this
input bool   InpIncludeManual=false;    // also close manual trades (magic 0)
input bool   InpDeletePending=true;
input int    InpTimerSeconds=2;
input string InpTestEvents="";          // TESTER ONLY: "yyyy.mm.dd hh:mi|USD;yyyy.mm.dd hh:mi|GBP" in SERVER time
input bool   InpTestOpen=false;         // TESTER ONLY: opens 0.01 test positions so the closing / blocking can be audited

struct NGEvent { datetime t; string ccy; string title; };
NGEvent g_ev[];
datetime g_loaded=0,g_fetched=0,g_lastWarn=0,g_lastTest=0;
long g_closed=0,g_deleted=0,g_blocks=0,g_testOpen=0,g_testBlocked=0;
CTrade g_trade;

int SrvOffset()
  {
   if(MQLInfoInteger(MQL_TESTER)) return 0;
   datetime s=TimeTradeServer(),u=TimeGMT(); if(s<=0||u<=0) return 0;
   return (int)MathRound((double)(s-u)/1800.0)*1800;
  }

bool ImpactWanted(string impact)
  {
   string list=","+InpImpacts+","; StringToUpper(list); StringToUpper(impact); StringTrimLeft(impact); StringTrimRight(impact);
   return StringFind(list,","+impact+",")>=0;
  }

void AddEvent(datetime t,string ccy,string title)
  {
   int n=ArraySize(g_ev); ArrayResize(g_ev,n+1); g_ev[n].t=t; StringToUpper(ccy); g_ev[n].ccy=ccy; g_ev[n].title=title;
  }

void LoadCalendar()
  {
   ArrayResize(g_ev,0); g_loaded=TimeCurrent();
   if(MQLInfoInteger(MQL_TESTER) && InpTestEvents!="")
     {
      string items[]; int n=StringSplit(InpTestEvents,';',items);
      for(int i=0;i<n;i++){string f[];if(StringSplit(items[i],'|',f)==2)AddEvent(StringToTime(f[0]),f[1],"test event");}
      g_fetched=TimeCurrent(); return;
     }
   int h=FileOpen(InpCalendarFile,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ);
   if(h==INVALID_HANDLE){g_fetched=0;return;}
   int off=SrvOffset();
   while(!FileIsEnding(h))
     {
      string line=FileReadString(h); if(StringLen(line)<5) continue;
      if(StringGetCharacter(line,0)=='#'){int k=StringFind(line,"fetched_utc=");if(k>=0)g_fetched=(datetime)StringToInteger(StringSubstr(line,k+12))+off;continue;}
      string f[]; if(StringSplit(line,',',f)<3) continue;
      long utc=StringToInteger(f[0]); if(utc<=0||!ImpactWanted(f[2])) continue;
      AddEvent((datetime)(utc+off),f[1],ArraySize(f)>3?f[3]:"");
     }
   FileClose(h);
  }

bool Affected(const string symbol,const string ccy)
  {
   return SymbolInfoString(symbol,SYMBOL_CURRENCY_BASE)==ccy || SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT)==ccy;
  }

void Block(const string symbol,datetime until)
  {
   string key="CNB_"+symbol;
   if(!GlobalVariableCheck(key) || (datetime)GlobalVariableGet(key)<until){GlobalVariableSet(key,(double)until);g_blocks++;}
  }

void Flatten(const string ccy)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i); if(t==0) continue;
      string s=PositionGetString(POSITION_SYMBOL); long m=PositionGetInteger(POSITION_MAGIC);
      if((m==0&&!InpIncludeManual)||!Affected(s,ccy)) continue;
      if(g_trade.PositionClose(t,100)&&g_trade.ResultRetcode()==TRADE_RETCODE_DONE){g_closed++;PrintFormat("Calyx News Guard: closed #%I64u %s (magic %I64d) before %s news",t,s,m,ccy);}
     }
   if(!InpDeletePending) return;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong t=OrderGetTicket(i); if(t==0) continue;
      string s=OrderGetString(ORDER_SYMBOL); long m=OrderGetInteger(ORDER_MAGIC);
      if((m==0&&!InpIncludeManual)||!Affected(s,ccy)) continue;
      if(g_trade.OrderDelete(t)){g_deleted++;PrintFormat("Calyx News Guard: deleted pending #%I64u %s before %s news",t,s,ccy);}
     }
  }

void Tick()
  {
   if(!InpEnabled) return;
   if(TimeCurrent()-g_loaded>600) LoadCalendar();
   datetime now=TimeCurrent(); string next=""; int shown=0;
   for(int i=0;i<ArraySize(g_ev);i++)
     {
      datetime ws=g_ev[i].t-InpBeforeMinutes*60, we=g_ev[i].t+InpAfterMinutes*60, lead=ws-InpCloseLeadSeconds;
      if(now>=lead && now<we)
        {
         for(int k=SymbolsTotal(true)-1;k>=0;k--){string s=SymbolName(k,true);if(Affected(s,g_ev[i].ccy))Block(s,we);}
         for(int k=PositionsTotal()-1;k>=0;k--){if(PositionGetTicket(k)==0)continue;string s=PositionGetString(POSITION_SYMBOL);if(Affected(s,g_ev[i].ccy))Block(s,we);}
         if(now<ws) Flatten(g_ev[i].ccy);                // before the window only: inside it no execution is allowed
        }
      if(g_ev[i].t>=now && shown<3){next+=StringFormat("\n  %s %s %s",TimeToString(g_ev[i].t,TIME_DATE|TIME_MINUTES),g_ev[i].ccy,g_ev[i].title);shown++;}
     }
   bool stale=(!MQLInfoInteger(MQL_TESTER)) && (g_fetched==0 || now-g_fetched>InpStaleHours*3600);
   if(stale && now-g_lastWarn>3600){g_lastWarn=now;Print("Calyx News Guard WARNING: calendar file missing or older than ",InpStaleHours," h - run Update News Calendar.bat (daily).");}
   Comment(StringFormat("Calyx News Guard: %s  window -%d/+%d min, close %d s before; %d events loaded%s%s",InpEnabled?"ON":"OFF",InpBeforeMinutes,InpAfterMinutes,InpCloseLeadSeconds,ArraySize(g_ev),
           stale?"\n  WARNING: calendar missing / stale - run Update News Calendar.bat":"",next==""?"\n  no upcoming events in the file":"\n next:"+next));
   if(MQLInfoInteger(MQL_TESTER) && InpTestOpen && now-g_lastTest>=900)
     {
      g_lastTest=now; MqlTradeRequest r={}; MqlTradeResult res={};
      string key="CNB_"+_Symbol; bool blocked=GlobalVariableCheck(key)&&(datetime)GlobalVariableGet(key)>now;
      if(blocked){g_testBlocked++;return;}                    // a Calyx EA would be refused here (InpCalyxNewsBlock)
      if(PositionsTotal()==0){g_trade.SetExpertMagicNumber(777);if(g_trade.Buy(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)))g_testOpen++;}
     }
  }

int OnInit(){g_trade.SetDeviationInPoints(100);LoadCalendar();EventSetTimer(MathMax(1,InpTimerSeconds));Tick();return INIT_SUCCEEDED;}
void OnTimer(){Tick();}
void OnTick(){if(MQLInfoInteger(MQL_TESTER))Tick();}
void OnDeinit(const int r)
  {
   EventKillTimer(); Comment("");
   PrintFormat("CALYX_NEWS_GUARD_SUMMARY events=%d closed=%I64d deleted=%I64d blocks=%I64d test_open=%I64d test_blocked=%I64d",ArraySize(g_ev),g_closed,g_deleted,g_blocks,g_testOpen,g_testBlocked);
  }

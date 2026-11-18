//+------------------------------------------------------------------+
//| Calyx No Opposite (2026-11-17)                                   |
//| Owner: "build the no opposite trade rule into the EAs".          |
//| FundingPips support (2026-11-17): a buy and a sell on the same    |
//| symbol at the same time is forbidden hedging, no exceptions,     |
//| even from two independent strategies.                            |
//|                                                                  |
//| InpCalyxNoOpposite=false (default): every order goes exactly the |
//| old way (::OrderSend / ::OrderSendAsync), so results are the     |
//| tested ones.                                                     |
//| InpCalyxNoOpposite=true:                                         |
//|  1. a NEW market entry or pending order is refused while ANY     |
//|     position (any EA, any magic, manual too) is open on the same |
//|     symbol in the opposite direction. Same-direction stacking,   |
//|     closes, partial closes, SL/TP changes and deletions pass.    |
//|  2. the check and the send run under one account-wide lock file  |
//|     (Common\Files), so two EAs cannot open opposite sides at the |
//|     same moment.                                                 |
//|  3. CNO_Tick (wrapper OnTick, at most once per second): deletes  |
//|     this EA's own pending orders that face an opposite open      |
//|     position, and closes this EA's own position if it became the |
//|     newer side of an opposite pair (a pending fill in the same   |
//|     second as another EA's entry). Other EAs' orders and         |
//|     positions are never touched.                                 |
//| Guarded builds: the check runs inside the guard's own lock; the  |
//| guards refuse pending orders, so only rule 1 applies there.      |
//+------------------------------------------------------------------+
#ifndef CALYX_NO_OPPOSITE_MQH
#define CALYX_NO_OPPOSITE_MQH

input bool InpCalyxNoOpposite=false; // Calyx: never hold a buy and a sell on the same symbol (FundingPips hedging rule); installer sets it

ulong    cno_magics[];
datetime cno_last_tick=0;
datetime cno_last_print=0;
bool     cno_loaded=false;

int CNO_Dir(const long type)
  {
   if(type==ORDER_TYPE_BUY || type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_BUY_STOP_LIMIT)
      return 1;
   if(type==ORDER_TYPE_SELL || type==ORDER_TYPE_SELL_LIMIT || type==ORDER_TYPE_SELL_STOP || type==ORDER_TYPE_SELL_STOP_LIMIT)
      return -1;
   return 0;
  }

uint CNO_Hash(const string s)
  {
   uint h=2166136261;
   for(int i=0;i<StringLen(s);i++)
      h=(h^(uint)StringGetCharacter(s,i))*16777619;
   return h;
  }

string CNO_Key(const ulong magic)
  {
   return StringFormat("CNO_%u_%I64u",CNO_Hash(MQLInfoString(MQL_PROGRAM_NAME)+"|"+_Symbol),magic);
  }

void CNO_Load()
  {
   if(cno_loaded) return;
   cno_loaded=true;
   string prefix=StringFormat("CNO_%u_",CNO_Hash(MQLInfoString(MQL_PROGRAM_NAME)+"|"+_Symbol));
   for(int i=GlobalVariablesTotal()-1;i>=0;i--)
     {
      string name=GlobalVariableName(i);
      if(StringFind(name,prefix)!=0) continue;
      ulong magic=(ulong)StringToInteger(StringSubstr(name,StringLen(prefix)));
      bool known=false;
      for(int k=0;k<ArraySize(cno_magics);k++) if(cno_magics[k]==magic) known=true;
      if(!known){int n=ArraySize(cno_magics);ArrayResize(cno_magics,n+1);cno_magics[n]=magic;}
     }
  }

void CNO_Remember(const ulong magic)
  {
   if(magic==0) return;
   CNO_Load();
   for(int k=0;k<ArraySize(cno_magics);k++) if(cno_magics[k]==magic) return;
   int n=ArraySize(cno_magics);ArrayResize(cno_magics,n+1);cno_magics[n]=magic;
   if(!MQLInfoInteger(MQL_TESTER)) GlobalVariableSet(CNO_Key(magic),(double)TimeCurrent());
  }

bool CNO_Mine(const ulong magic)
  {
   CNO_Load();
   for(int k=0;k<ArraySize(cno_magics);k++) if(cno_magics[k]==magic) return true;
   return false;
  }

// true when any open position on symbol faces direction dir. Restores the caller's selected position.
bool CNO_OppositeOpen(const string symbol,const int dir)
  {
   if(dir==0) return false;
   ulong keep=(ulong)PositionGetInteger(POSITION_TICKET);
   bool found=false;
   for(int i=PositionsTotal()-1;i>=0 && !found;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=symbol) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      if((dir>0 && type==POSITION_TYPE_SELL) || (dir<0 && type==POSITION_TYPE_BUY)) found=true;
     }
   if(keep>0) PositionSelectByTicket(keep);
   return found;
  }

void CNO_Say(const string text)
  {
   if(TimeCurrent()-cno_last_print<60) return;
   cno_last_print=TimeCurrent();
   Print("Calyx no-opposite: ",text);
  }

bool CNO_Reject(MqlTradeResult &result,const string why)
  {
   ZeroMemory(result);
   result.retcode=TRADE_RETCODE_REJECT;
   result.comment="Calyx no-opposite: "+why;
   CNO_Say(why);
   return false;
  }

int CNO_Lock()
  {
   string name="CalyxNoOpposite-"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+".lock";
   for(int k=0;k<40;k++)
     {
      int h=FileOpen(name,FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
      if(h!=INVALID_HANDLE) return h;
      Sleep(25);
     }
   return INVALID_HANDLE;
  }

bool CNO_IsEntry(const MqlTradeRequest &request)
  {
   return (request.action==TRADE_ACTION_DEAL && request.position==0) || request.action==TRADE_ACTION_PENDING;
  }

// Replacement for OrderSend / OrderSendAsync in the no-guard wrappers.
bool CalyxNoOppOrderSend(const MqlTradeRequest &request,MqlTradeResult &result,const bool async=false)
  {
   if(!InpCalyxNoOpposite || !CNO_IsEntry(request))
     {
      bool sent=async ? ::OrderSendAsync(request,result) : ::OrderSend(request,result);
      if(sent && InpCalyxNoOpposite) CNO_Remember(request.magic);
      return sent;
     }
   int lock=CNO_Lock();
   if(lock==INVALID_HANDLE) return CNO_Reject(result,"account lock busy; entry skipped");
   if(CNO_OppositeOpen(request.symbol,CNO_Dir(request.type)))
     {
      FileClose(lock);
      return CNO_Reject(result,"opposite position open on "+request.symbol+"; entry refused");
     }
   bool ok=async ? ::OrderSendAsync(request,result) : ::OrderSend(request,result);
   if(ok) CNO_Remember(request.magic);
   FileClose(lock);
   return ok;
  }

// Wrapper OnTick (no-guard builds). Only this EA's own orders / positions (magics it has sent) are touched.
void CNO_Tick()
  {
   if(!InpCalyxNoOpposite || TimeCurrent()==cno_last_tick) return;
   cno_last_tick=TimeCurrent();
   CNO_Load();
   if(ArraySize(cno_magics)==0) return;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || !CNO_Mine((ulong)OrderGetInteger(ORDER_MAGIC))) continue;
      string symbol=OrderGetString(ORDER_SYMBOL);
      if(!CNO_OppositeOpen(symbol,CNO_Dir(OrderGetInteger(ORDER_TYPE)))) continue;
      MqlTradeRequest r={};MqlTradeResult res={};
      r.action=TRADE_ACTION_REMOVE;r.order=ticket;
      if(::OrderSend(r,res)) PrintFormat("Calyx no-opposite: deleted own pending order #%I64u on %s (opposite position open)",ticket,symbol);
     }
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !CNO_Mine((ulong)PositionGetInteger(POSITION_MAGIC))) continue;
      string symbol=PositionGetString(POSITION_SYMBOL);
      long type=PositionGetInteger(POSITION_TYPE);
      long opened=PositionGetInteger(POSITION_TIME_MSC);
      double volume=PositionGetDouble(POSITION_VOLUME);
      bool older=false;
      for(int j=PositionsTotal()-1;j>=0 && !older;j--)
        {
         ulong other=PositionGetTicket(j);
         if(other==0 || other==ticket || PositionGetString(POSITION_SYMBOL)!=symbol || PositionGetInteger(POSITION_TYPE)==type) continue;
         if(PositionGetInteger(POSITION_TIME_MSC)<opened || (PositionGetInteger(POSITION_TIME_MSC)==opened && other<ticket)) older=true;
        }
      if(!older) continue;
      MqlTradeRequest r={};MqlTradeResult res={};
      r.action=TRADE_ACTION_DEAL;r.position=ticket;r.symbol=symbol;r.volume=volume;r.deviation=50;
      r.magic=0;
      r.type=type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      r.price=type==POSITION_TYPE_BUY ? SymbolInfoDouble(symbol,SYMBOL_BID) : SymbolInfoDouble(symbol,SYMBOL_ASK);
      long fill=SymbolInfoInteger(symbol,SYMBOL_FILLING_MODE);
      r.type_filling=(fill&SYMBOL_FILLING_FOK)!=0 ? ORDER_FILLING_FOK : ((fill&SYMBOL_FILLING_IOC)!=0 ? ORDER_FILLING_IOC : ORDER_FILLING_RETURN);
      if(::OrderSend(r,res)) PrintFormat("Calyx no-opposite: closed own position #%I64u on %s - it became the newer side of an opposite pair",ticket,symbol);
      else PrintFormat("Calyx no-opposite: could not close own opposite position #%I64u (%u) - close it manually",ticket,res.retcode);
     }
  }

#endif

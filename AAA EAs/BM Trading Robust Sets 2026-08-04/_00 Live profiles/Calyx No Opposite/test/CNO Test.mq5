//+------------------------------------------------------------------+
//| CNO Test: tester harness for CalyxNoOpposite.mqh + CNO_Trade.mqh |
//| Three CTrade objects (magics 111/222/333) play three EAs on one  |
//| symbol. Each stage runs once, 60 s apart; CNO_Tick runs on every |
//| tick as in the wrappers. Prints CNO_TEST <stage> PASS/FAIL.      |
//| Expectations depend on InpCalyxNoOpposite (ON = rule, OFF = the  |
//| old behaviour: everything goes through).                         |
//+------------------------------------------------------------------+
#property strict
#include "../CNO_Trade.mqh"

CTrade t1,t2,t3;
int stage=0,fails=0;
datetime nextAt=0;

void Check(const string what,const bool ok)
  {
   PrintFormat("CNO_TEST %s %s",what,ok?"PASS":"FAIL");
   if(!ok) fails++;
  }

int Count(const long kind,const ulong magic,const bool orders)
  {
   int n=0;
   if(orders)
     {
      for(int i=OrdersTotal()-1;i>=0;i--){ulong tk=OrderGetTicket(i);if(tk>0 && OrderGetInteger(ORDER_TYPE)==kind && (magic==0 || (ulong)OrderGetInteger(ORDER_MAGIC)==magic))n++;}
     }
   else
     {
      for(int i=PositionsTotal()-1;i>=0;i--){ulong tk=PositionGetTicket(i);if(tk>0 && PositionGetInteger(POSITION_TYPE)==kind && (magic==0 || (ulong)PositionGetInteger(POSITION_MAGIC)==magic))n++;}
     }
   return n;
  }

void CloseAll()
  {
   for(int i=PositionsTotal()-1;i>=0;i--){ulong tk=PositionGetTicket(i);if(tk>0)t1.PositionClose(tk);}
   for(int i=OrdersTotal()-1;i>=0;i--){ulong tk=OrderGetTicket(i);if(tk>0)t1.OrderDelete(tk);}
  }

int OnInit()
  {
   t1.SetExpertMagicNumber(111);t2.SetExpertMagicNumber(222);t3.SetExpertMagicNumber(333);
   PrintFormat("CNO_TEST start rule=%s",InpCalyxNoOpposite?"ON":"OFF");
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   CNO_Tick();
   if(stage>10 || TimeCurrent()<nextAt) return;
   nextAt=TimeCurrent()+60;
   bool on=InpCalyxNoOpposite;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID),pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double lot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   switch(stage)
     {
      case 0: Check("s0 buy market (first position)",t1.Buy(lot)); break;
      case 1: Check(on?"s1 sell market refused (buy open)":"s1 sell market allowed (rule off)",t2.Sell(lot)==!on); break;
      case 2: Check(on?"s2 sell stop refused (buy open)":"s2 sell stop allowed (rule off)",t2.SellStop(lot,NormalizeDouble(bid-2000*pt,digits))==!on); break;
      case 3: Check("s3 second buy allowed (same side)",t3.Buy(lot)); break;
      case 4: CloseAll(); break;
      case 5: Check("s5 flat after closes/deletes",PositionsTotal()==0 && OrdersTotal()==0);
              Check("s5 own buy stop placed",t1.BuyStop(lot,NormalizeDouble(ask+3000*pt,digits))); break;
      case 6: Check("s6 sell market allowed (only a pending buy exists)",t3.Sell(lot)); break;
      case 7: Check(on?"s7 own buy stop deleted by CNO_Tick":"s7 buy stop kept (rule off)",Count(ORDER_TYPE_BUY_STOP,111,true)==(on?0:1)); break;
      case 8:
        {
         MqlTradeRequest r={};MqlTradeResult res={};
         r.action=TRADE_ACTION_DEAL;r.symbol=_Symbol;r.volume=lot;r.type=ORDER_TYPE_BUY;r.price=ask;r.magic=111;r.deviation=50;
         long fill=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
         r.type_filling=(fill&SYMBOL_FILLING_FOK)!=0?ORDER_FILLING_FOK:((fill&SYMBOL_FILLING_IOC)!=0?ORDER_FILLING_IOC:ORDER_FILLING_RETURN);
         Check("s8 bypass buy sent directly (simulated same-second fill)",::OrderSend(r,res));
         break;
        }
      case 9: Check(on?"s9 own newer buy closed by CNO_Tick":"s9 newer buy kept (rule off)",Count(POSITION_TYPE_BUY,111,false)==(on?0:1));
              Check("s9 older sell untouched",Count(POSITION_TYPE_SELL,333,false)==1); break;
      case 10: CloseAll(); PrintFormat("CNO_TEST DONE fails=%d",fails); break;
     }
   stage++;
  }

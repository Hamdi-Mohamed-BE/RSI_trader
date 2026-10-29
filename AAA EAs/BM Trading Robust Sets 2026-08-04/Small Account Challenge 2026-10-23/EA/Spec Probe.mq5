#property strict
// Research only: prints broker symbol rules in the isolated tester, then stops. No orders.
int OnInit(){
   string s[]={"USTEC","XAUUSD","USDJPY","EURUSD"};
   for(int i=0;i<ArraySize(s);i++){
      SymbolSelect(s[i],true);
      double mi=0,ma=0;
      bool okb=OrderCalcMargin(ORDER_TYPE_BUY,s[i],1.0,SymbolInfoDouble(s[i],SYMBOL_ASK),mi);
      PrintFormat("SPEC sym=%s min=%.2f step=%.2f max=%.2f contract=%.2f digits=%d point=%.10f tickvalue=%.6f ticksize=%.10f margin_1lot=%.4f ok=%d stops=%d leverage=%d",
         s[i],SymbolInfoDouble(s[i],SYMBOL_VOLUME_MIN),SymbolInfoDouble(s[i],SYMBOL_VOLUME_STEP),SymbolInfoDouble(s[i],SYMBOL_VOLUME_MAX),
         SymbolInfoDouble(s[i],SYMBOL_TRADE_CONTRACT_SIZE),(int)SymbolInfoInteger(s[i],SYMBOL_DIGITS),SymbolInfoDouble(s[i],SYMBOL_POINT),
         SymbolInfoDouble(s[i],SYMBOL_TRADE_TICK_VALUE),SymbolInfoDouble(s[i],SYMBOL_TRADE_TICK_SIZE),mi,okb,(int)SymbolInfoInteger(s[i],SYMBOL_TRADE_STOPS_LEVEL),(int)AccountInfoInteger(ACCOUNT_LEVERAGE));
   }
   PrintFormat("SPEC account stopout_mode=%d stopout_level=%.2f margin_call=%.2f currency=%s",(int)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE),AccountInfoDouble(ACCOUNT_MARGIN_SO_SO),AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL),AccountInfoString(ACCOUNT_CURRENCY));
   return INIT_SUCCEEDED;
}
void OnTick(){ExpertRemove();}

#define OnInit OriginalInit
#define OnTick OriginalTick
#define OnTimer OriginalTimer
#define OnDeinit OriginalDeinit
#include "Base.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
int export_file=INVALID_HANDLE;
int EventWindow() {
 datetime now=TimeCurrent();int left=0,right=ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);
 while(left<right){int mid=(left+right)/2;if(NP_GENERATED_EVENT_UTC_EPOCHS[mid]<now-905)left=mid+1;else right=mid;}
 if(left<ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS) && now>=NP_GENERATED_EVENT_UTC_EPOCHS[left]-185 && now<=NP_GENERATED_EVENT_UTC_EPOCHS[left]+905)return left;
 return -1;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 int result=OriginalInit();if(result!=INIT_SUCCEEDED)return result;
 export_file=FileOpen("news-event-quotes-20260919.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
 if(export_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(export_file,"event","time_msc","bid","ask","current_high","current_low","previous_high","previous_low");
 PrintFormat("NEWS_SPEC|point=%.8f|ticksize=%.8f|contract=%.2f|lot_min=%.4f|lot_step=%.4f|stops=%d|freeze=%d",_Point,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL));
 return INIT_SUCCEEDED;
}
void OnTick(){
 int index=EventWindow();if(index<0)return;
 MqlTick q;if(SymbolInfoTick(_Symbol,q))FileWrite(export_file,index,q.time_msc,DoubleToString(q.bid,_Digits),DoubleToString(q.ask,_Digits),DoubleToString(iHigh(_Symbol,PERIOD_M1,0),_Digits),DoubleToString(iLow(_Symbol,PERIOD_M1,0),_Digits),DoubleToString(iHigh(_Symbol,PERIOD_M1,1),_Digits),DoubleToString(iLow(_Symbol,PERIOD_M1,1),_Digits));
 OriginalTick();
}
void OnTimer(){if(EventWindow()>=0)OriginalTimer();}
void OnDeinit(const int reason){if(export_file!=INVALID_HANDLE)FileClose(export_file);OriginalDeinit(reason);}

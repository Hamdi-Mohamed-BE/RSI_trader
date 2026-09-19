#define OnInit OriginalInit
#define OnTick OriginalTick
#define OnTimer OriginalTimer
#define OnDeinit OriginalDeinit
#include "CandidateBase.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
int EventWindow() {
 datetime now=TimeCurrent();int left=0,right=ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);
 while(left<right){int mid=(left+right)/2;if(NP_GENERATED_EVENT_UTC_EPOCHS[mid]<now-905)left=mid+1;else right=mid;}
 if(left<ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS) && now>=NP_GENERATED_EVENT_UTC_EPOCHS[left]-185 && now<=NP_GENERATED_EVENT_UTC_EPOCHS[left]+905)return left;
 return -1;
}
void ApplySettings(const string kind) {
if(kind=="NFP") {InpPlacementLeadSeconds=90;NPX_Anchor=1;InpEntryOffsetPrice=0.0002000000;InpStopLossPrice=0.0001000000;NPX_TPR=0.0;InpTrailStartR=1.5;InpTrailDistancePrice=0.0008000000;InpForceCloseSecondsAfterEvent=600;}
if(kind=="CPI") {InpPlacementLeadSeconds=30;NPX_Anchor=1;InpEntryOffsetPrice=0.0006000000;InpStopLossPrice=0.0001000000;NPX_TPR=0.0;InpTrailStartR=1.0;InpTrailDistancePrice=0.0006000000;InpForceCloseSecondsAfterEvent=60;}
if(kind=="FOMC") {InpPlacementLeadSeconds=120;NPX_Anchor=1;InpEntryOffsetPrice=0.0002000000;InpStopLossPrice=0.0001000000;NPX_TPR=7.0;InpTrailStartR=100000;InpTrailDistancePrice=0.0002000000;InpForceCloseSecondsAfterEvent=180;}
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTick();}
void OnTimer(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}

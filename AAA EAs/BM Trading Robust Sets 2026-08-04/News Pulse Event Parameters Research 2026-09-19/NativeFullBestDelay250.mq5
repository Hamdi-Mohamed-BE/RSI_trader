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
if(kind=="NFP") {InpPlacementLeadSeconds=10;NPX_Anchor=2;InpEntryOffsetPrice=2.0;InpStopLossPrice=2.0;NPX_TPR=0.0;InpTrailStartR=100000;InpTrailDistancePrice=4.0;InpForceCloseSecondsAfterEvent=60;}
if(kind=="CPI") {InpPlacementLeadSeconds=5;NPX_Anchor=2;InpEntryOffsetPrice=1.0;InpStopLossPrice=2.0;NPX_TPR=0.0;InpTrailStartR=1.0;InpTrailDistancePrice=10.0;InpForceCloseSecondsAfterEvent=300;}
if(kind=="FOMC") {InpPlacementLeadSeconds=60;NPX_Anchor=0;InpEntryOffsetPrice=1.0;InpStopLossPrice=2.0;NPX_TPR=5.5;InpTrailStartR=0.5;InpTrailDistancePrice=4.0;InpForceCloseSecondsAfterEvent=120;}
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTick();}
void OnTimer(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}

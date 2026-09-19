#define OnInit StudyBaseOnInit
#define OnTick StudyBaseOnTick
#define OnDeinit StudyBaseOnDeinit
#include "..\Sell Nasdaq 15min Research 2026-09-08\Dynamic Exit Research\EA\Sell Nasdaq 15min Dynamic Exit Research EA.mq5"
#undef OnInit
#undef OnTick
#undef OnDeinit
#include "StudyAudit.mqh"
int OnInit(){if(!StudyGuard())return INIT_FAILED;int code=StudyBaseOnInit();if(code!=INIT_SUCCEEDED)return code;return StudyInit();}
void OnTick(){StudyObserve();StudyBaseOnTick();StudyObserve();}
void OnDeinit(const int reason){StudyFinish();StudyBaseOnDeinit(reason);}

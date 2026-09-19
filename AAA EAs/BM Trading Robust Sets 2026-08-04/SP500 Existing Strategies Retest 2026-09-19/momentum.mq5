#define OnInit StudyBaseOnInit
#define OnTick StudyBaseOnTick
#define OnDeinit StudyBaseOnDeinit
#include "..\Active Portfolio Full Pipeline 2026-09-05\11 Nasdaq 5M Candle Momentum\EA\Nasdaq 5M Candle Momentum Audit EA.mq5"
#undef OnInit
#undef OnTick
#undef OnDeinit
#include "StudyAudit.mqh"
int OnInit(){if(!StudyGuard())return INIT_FAILED;int code=StudyBaseOnInit();if(code!=INIT_SUCCEEDED)return code;return StudyInit();}
void OnTick(){StudyObserve();StudyBaseOnTick();StudyObserve();}
void OnDeinit(const int reason){StudyFinish();StudyBaseOnDeinit(reason);}

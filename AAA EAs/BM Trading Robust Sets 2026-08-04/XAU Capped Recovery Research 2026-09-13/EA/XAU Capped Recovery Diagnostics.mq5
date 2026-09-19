#include "Optimization Core.mqh"
input int InpResearchCase=0;
input long InpBatchMagic=94000000;
int OnInit()
{
 if(InpResearchCase==0)InpMultiplier=2;
 else if(InpResearchCase==1)InpOriginalExit=true;
 else if(InpResearchCase==2)InpBasketLoss=30;
 else if(InpResearchCase==3)InpDailyProfit=30;
 else if(InpResearchCase==4)InpDailyProfit=0;
 else return INIT_PARAMETERS_INCORRECT;
 InpMagic=InpBatchMagic+InpResearchCase;
 return BaseInit();
}
double OnTester(){return (Balance()-initial)/(1+maxDDCash);}

#include "Optimization Core.mqh"
input int InpResearchCase=0;
input long InpBatchMagic=91000000;
int OnInit()
{
 int spacing=InpResearchCase/3,profit=InpResearchCase%3;
 InpStep=spacing==0?10:(spacing==1?20:(spacing==2?30:10));
 InpATRStep=spacing==3;InpBasketProfit=10*(profit+1);
 InpMagic=InpBatchMagic+InpResearchCase;
 return BaseInit();
}
double OnTester(){return (Balance()-initial)/(1+maxDDCash);}

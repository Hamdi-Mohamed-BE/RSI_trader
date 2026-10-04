#ifndef CALYX_ADX_DI_STUDY
#define CALYX_ADX_DI_STUDY
#include <Trade/Trade.mqh>
input group "Research only - ADX DI admission"
input int InpStudyADXGate=0; // 0=off, 1=floor, 2=ceiling
input double InpStudyADXLevel=20.0;
input bool InpStudyDI=false;
input ENUM_TIMEFRAMES InpStudyTF=PERIOD_H4;
input string InpStudyTag="default";
int study_adx=INVALID_HANDLE,study_file=INVALID_HANDLE;
bool StudyInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) {Print("Research only: no live initialization");return false;}
   if(InpStudyADXGate<0 || InpStudyADXGate>2 || InpStudyADXLevel<0 || InpStudyADXLevel>100) return false;
   study_adx=iADX(_Symbol,InpStudyTF,14);
   if(study_adx==INVALID_HANDLE) return false;
   study_file=FileOpen("ADXDI20261003-"+InpStudyTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(study_file==INVALID_HANDLE) return false;
   FileWrite(study_file,"event","epoch","bar_epoch","tf_seconds","direction","valid","adx","plus_di","minus_di","allowed","retcode");
   return true;
}
void StudyClose()
{
   if(study_adx!=INVALID_HANDLE) IndicatorRelease(study_adx);
   if(study_file!=INVALID_HANDLE) FileClose(study_file);
}
bool StudyAllow(const int direction)
{
   double a[1],p[1],m[1];
   datetime bar=iTime(_Symbol,InpStudyTF,1);
   int seconds=PeriodSeconds(InpStudyTF);
   bool valid=bar>0 && seconds>0 && bar+seconds<=TimeCurrent();
   valid=valid && CopyBuffer(study_adx,0,1,1,a)==1 && CopyBuffer(study_adx,1,1,1,p)==1 && CopyBuffer(study_adx,2,1,1,m)==1;
   double av=0,pv=0,mv=0;
   if(valid)
   {
      av=a[0];pv=p[0];mv=m[0];
      valid=MathIsValidNumber(av) && MathIsValidNumber(pv) && MathIsValidNumber(mv) && av>=0 && av<=100 && pv>=0 && pv<=100 && mv>=0 && mv<=100;
   }
   bool enabled=InpStudyADXGate!=0 || InpStudyDI;
   bool allowed=!enabled || valid;
   if(enabled && valid)
   {
      if(InpStudyADXGate==1 && av<InpStudyADXLevel) allowed=false;
      if(InpStudyADXGate==2 && av>InpStudyADXLevel) allowed=false;
      if(InpStudyDI && !((direction>0 && pv>mv) || (direction<0 && mv>pv))) allowed=false;
   }
   FileWrite(study_file,"gate",(long)TimeCurrent(),(long)bar,seconds,direction,(int)valid,DoubleToString(av,10),DoubleToString(pv,10),DoubleToString(mv,10),(int)allowed,0);
   return allowed;
}
bool StudyBuy(CTrade &client,const double volume,const string symbol,const double price,const double sl,const double tp,const string comment)
{
   bool ok=client.Buy(volume,symbol,price,sl,tp,comment);
   FileWrite(study_file,"entry",(long)TimeCurrent(),0,0,1,0,0,0,0,(int)ok,client.ResultRetcode());
   return ok;
}
bool StudySell(CTrade &client,const double volume,const string symbol,const double price,const double sl,const double tp,const string comment)
{
   bool ok=client.Sell(volume,symbol,price,sl,tp,comment);
   FileWrite(study_file,"entry",(long)TimeCurrent(),0,0,-1,0,0,0,0,(int)ok,client.ResultRetcode());
   return ok;
}
#endif

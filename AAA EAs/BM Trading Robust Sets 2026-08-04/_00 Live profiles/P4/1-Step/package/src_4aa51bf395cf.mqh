#ifndef CALYX_ADMISSION_20261003
#define CALYX_ADMISSION_20261003
input group "ADX / DI entry admission"
input bool InpUseADXFilter=CALYX_DEFAULT_ADX;
input double InpADXMinimum=CALYX_DEFAULT_ADX_LEVEL;
input bool InpRequireDIAgreement=CALYX_DEFAULT_DI;
input ENUM_TIMEFRAMES InpADXTimeframe=CALYX_DEFAULT_ADX_TF;
int calyx_admission_handle=INVALID_HANDLE;
bool CalyxAdmissionInit()
{
   if(InpADXMinimum<0 || InpADXMinimum>100 || !MathIsValidNumber(InpADXMinimum)) return false;
   if(!InpUseADXFilter && !InpRequireDIAgreement) return true;
   calyx_admission_handle=iADX(_Symbol,InpADXTimeframe,14);
   return calyx_admission_handle!=INVALID_HANDLE;
}
void CalyxAdmissionClose()
{
   if(calyx_admission_handle!=INVALID_HANDLE) IndicatorRelease(calyx_admission_handle);
   calyx_admission_handle=INVALID_HANDLE;
}
bool CalyxAdmissionAllow(const int direction)
{
   // Entry gate only: existing position management is never blocked.
   if(!InpUseADXFilter && !InpRequireDIAgreement) return true;
   double a[1],p[1],m[1];
   datetime bar=iTime(_Symbol,InpADXTimeframe,1);
   int seconds=PeriodSeconds(InpADXTimeframe);
   bool valid=bar>0 && seconds>0 && bar+seconds<=TimeCurrent();
   valid=valid && CopyBuffer(calyx_admission_handle,0,1,1,a)==1 && CopyBuffer(calyx_admission_handle,1,1,1,p)==1 && CopyBuffer(calyx_admission_handle,2,1,1,m)==1;
   if(!valid) return false;
   valid=MathIsValidNumber(a[0]) && MathIsValidNumber(p[0]) && MathIsValidNumber(m[0]) && a[0]>=0 && a[0]<=100 && p[0]>=0 && p[0]<=100 && m[0]>=0 && m[0]<=100;
   if(!valid) return false;
   if(InpUseADXFilter && a[0]<InpADXMinimum) return false;
   if(InpRequireDIAgreement && !((direction>0 && p[0]>m[0]) || (direction<0 && m[0]>p[0]))) return false;
   return true;
}
#endif

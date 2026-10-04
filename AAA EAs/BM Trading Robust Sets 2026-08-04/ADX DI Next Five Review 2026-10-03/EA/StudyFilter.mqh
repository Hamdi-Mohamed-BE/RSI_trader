#ifndef CALYX_NEXT_ADX_DI_STUDY
#define CALYX_NEXT_ADX_DI_STUDY
input group "Research only - default OFF entry filters"
input int InpStudyADXGate=0; // 0 off; 1 floor; 3 rising versus previous completed bar
input double InpStudyADXLevel=20;
input bool InpStudyDI=false;
input ENUM_TIMEFRAMES InpStudyTF=PERIOD_M30;
input int InpStudyModule=0; // 0 all single-EA entries; 1 MOM only; 2 BRK only
input string InpStudyTag="default";
int study_handles[3],study_file=INVALID_HANDLE;
ENUM_TIMEFRAMES study_tfs[3];
bool StudyInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research copy only; live initialization refused");return false;}
 study_tfs[0]=InpStudyTF;study_tfs[1]=PERIOD_H4;study_tfs[2]=PERIOD_M15;
 for(int i=0;i<3;i++){study_handles[i]=iADX(_Symbol,study_tfs[i],14);if(study_handles[i]==INVALID_HANDLE)return false;}
 study_file=FileOpen("ADXDI_NEXT20261003-"+InpStudyTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(study_file==INVALID_HANDLE)return false;
 FileWrite(study_file,"event","epoch","bar_epoch","tf_seconds","direction","valid","adx","plus_di","minus_di","allowed","retcode","module","previous_adx");
 return true;
}
void StudyClose(){for(int i=0;i<3;i++)if(study_handles[i]!=INVALID_HANDLE)IndicatorRelease(study_handles[i]);if(study_file!=INVALID_HANDLE)FileClose(study_file);}
bool StudyAllow(const int direction,const ENUM_TIMEFRAMES timeframe=PERIOD_CURRENT,const int module=0){
 if(InpStudyModule!=0&&module!=InpStudyModule)return true;
 ENUM_TIMEFRAMES tf=timeframe==PERIOD_CURRENT?InpStudyTF:timeframe;
 int h=INVALID_HANDLE;for(int i=0;i<3;i++)if(study_tfs[i]==tf){h=study_handles[i];break;}
 double a[1],p[1],m[1],prev[1];datetime bar=iTime(_Symbol,tf,1);int sec=PeriodSeconds(tf);
 bool valid=bar>0&&sec>0&&bar+sec<=TimeCurrent()&&h!=INVALID_HANDLE;
 valid=valid&&CopyBuffer(h,0,1,1,a)==1&&CopyBuffer(h,1,1,1,p)==1&&CopyBuffer(h,2,1,1,m)==1&&CopyBuffer(h,0,2,1,prev)==1;
 double av=0,pv=0,mv=0,bv=0;if(valid){av=a[0];pv=p[0];mv=m[0];bv=prev[0];valid=MathIsValidNumber(av)&&MathIsValidNumber(pv)&&MathIsValidNumber(mv)&&MathIsValidNumber(bv)&&av>=0&&av<=100&&pv>=0&&pv<=100&&mv>=0&&mv<=100&&bv>=0&&bv<=100;}
 bool enabled=InpStudyADXGate!=0||InpStudyDI;bool allowed=!enabled||valid;
 if(enabled&&valid){if(InpStudyADXGate==1&&av<InpStudyADXLevel)allowed=false;if(InpStudyADXGate==3&&av<=bv)allowed=false;if(InpStudyDI&&!((direction>0&&pv>mv)||(direction<0&&mv>pv)))allowed=false;}
 FileWrite(study_file,"gate",(long)TimeCurrent(),(long)bar,sec,direction,(int)valid,DoubleToString(av,10),DoubleToString(pv,10),DoubleToString(mv,10),(int)allowed,0,module,DoubleToString(bv,10));
 return allowed;
}
#endif

"""Asserted source transformation; frozen raw file is never edited."""
from pathlib import Path
import re
from search_plan import FIELDS
R=Path(__file__).resolve().parent
def replace(text,old,new):
 assert text.count(old)==1,(old,text.count(old))
 return text.replace(old,new,1)
def build():
 text=(R.parent/'Gann Research.mq5').read_text(encoding='utf-8')
 text=re.sub(r'^input ', '', text,flags=re.M)
 extra=(R/'Extras.mqh').read_text();declarations,functions=extra.split('datetime Sunday(',1)
 text=replace(text,'CTrade trade;',declarations+'\nCTrade trade;')
 text=replace(text,'traded=false;arm_side=0;arm_age=0;','traded=false;trades_today=0;cue_side=0;arm_side=0;arm_age=0;')
 text=replace(text,'MathAbs(age-8)<=1 || MathAbs(age-16)<=1 || MathAbs(age-32)<=1','MathAbs(age-8)<=cWidth || MathAbs(age-16)<=cWidth || MathAbs(age-32)<=cWidth')
 text=replace(text,'if(age<1 || age>33)return false;','if(age<1 || age>32+cWidth)return false;')
 text=replace(text,'double fraction=InpIdea==0?0.125:0.25;','double fraction=cFraction;')
 text=text.replace('-0.1*atr', '-cBuffer*atr').replace('+0.1*atr','+cBuffer*atr')
 text=replace(text,'double entry=side>0?tick.ask:tick.bid;\n   double stop=Price(raw_stop);',
  'double entry=side>0?tick.ask:tick.bid;\n   if(!ApplyOptions(side,bars,atr,entry,raw_stop,raw_target,known,pivot,feature,age))return false;\n   double stop=Price(raw_stop);')
 text=replace(text,'double target=Price(raw_target>0?raw_target:entry+side*InpTargetR*risk);',
  'double target=(cExit==2 || cExit==3)?0:Price(raw_target>0?raw_target:entry+side*InpTargetR*risk);')
 text=replace(text,'target>tick.bid+guard && target>entry','(target==0 || (target>tick.bid+guard && target>entry))')
 text=replace(text,'target<tick.ask-guard && target<entry','(target==0 || (target<tick.ask-guard && target<entry))')
 text=replace(text,'traded=true;may_hold=true;opened_at=TimeCurrent();placed++;arm_side=0;',
  'trades_today++;traded=trades_today>=cCap;may_hold=true;opened_at=TimeCurrent();placed++;arm_side=0;\n      initial_risk=risk;peak_price=entry;partial_done=false;')
 text=replace(text,'entry-side*1.5*atr','entry-side*cStopScale*atr')
 text=replace(text,' || InpPivotNeighbours!=2','')
 text=replace(text,'if(InpIdea>=3 && InpIdea<=5 && InpSignalTF!=PERIOD_H1)return INIT_PARAMETERS_INCORRECT;','')
 text=replace(text,'if(InpIdea>=3 && InpIdea<=5)\n   {','if(true)\n   {')
 text=replace(text,'iMA(_Symbol,PERIOD_H1,12,0,MODE_EMA,PRICE_CLOSE)','iMA(_Symbol,InpSignalTF,cFast,0,MODE_EMA,PRICE_CLOSE)')
 text=replace(text,'iMA(_Symbol,PERIOD_H1,26,0,MODE_EMA,PRICE_CLOSE)','iMA(_Symbol,InpSignalTF,cSlow,0,MODE_EMA,PRICE_CLOSE)')
 text=replace(text,'if(atr_handle==INVALID_HANDLE)return INIT_FAILED;',
  'adx_handle=iADX(_Symbol,InpSignalTF,14);atr_long_handle=iATR(_Symbol,InpSignalTF,50);htf_handle=iMA(_Symbol,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE);\n   if(atr_handle==INVALID_HANDLE || adx_handle==INVALID_HANDLE || atr_long_handle==INVALID_HANDLE || htf_handle==INVALID_HANDLE)return INIT_FAILED;')
 text=text.replace('CalyxGann20261009','CalyxGannPipeline20261009')
 text=replace(text,'if(may_hold && ((close_at>0 && TimeCurrent()>=close_at)',
  'ExecuteCue();ManagePosition();\n   if(may_hold && ((cFlat>0 && close_at>0 && TimeCurrent()>=close_at)')
 text=replace(text,'if(current==0 || current==last_bar)return;last_bar=current;',
  'if(current==0 || current==last_bar)return;last_bar=current;')
 text=replace(text,' || traded)return;',' || traded || cue_side!=0)return;')
 text=replace(text,'if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);',
  'if(adx_handle!=INVALID_HANDLE)IndicatorRelease(adx_handle);if(atr_long_handle!=INVALID_HANDLE)IndicatorRelease(atr_long_handle);if(htf_handle!=INVALID_HANDLE)IndicatorRelease(htf_handle);\n   if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);')
 text+='\ndatetime Sunday('+functions
 assignments={'tf':'InpSignalTF=(ENUM_TIMEFRAMES)(int)v;','reference':'InpReferenceTF=(ENUM_TIMEFRAMES)(int)v;',
  'fraction':'cFraction=v;','buffer':'cBuffer=v;','entry':'cEntry=(int)v;','stop':'cStop=(int)v;',
  'stop_scale':'cStopScale=v;','management':'cManagement=(int)v;','trigger':'cTrigger=v;','trail':'cTrail=v;',
  'exit':'cExit=(int)v;','rr':'InpTargetR=v;','session':'cSession=(int)v;','direction':'cDirection=(int)v;',
  'filter':'cFilter=(int)v;','threshold':'','daily_cap':'cCap=(int)v;','hold':'InpMaxHoldMinutes=(int)v;',
  'flat':'cFlat=(int)v;','dow':'cDOW=(int)v;','width':'cWidth=(int)v;','ema_fast':'cFast=(int)v;','ema_slow':'cSlow=(int)v;'}
 text+='\nvoid LoadCase(){double v;'
 for i,k in enumerate(FIELDS):
  if k=='tf':code='int tf=(int)v;InpSignalTF=tf<60?(ENUM_TIMEFRAMES)tf:(tf==60?PERIOD_H1:PERIOD_H4);'
  else:code=assignments[k]
  text+=f'v=C[InpCase][{i}];{code}\n'
 text+='InpRiskPercent=InpRiskPct;InpIdea=InpBot;InpSignalAuditTag=InpTag+"-"+IntegerToString(InpCase);}\n'
 return text

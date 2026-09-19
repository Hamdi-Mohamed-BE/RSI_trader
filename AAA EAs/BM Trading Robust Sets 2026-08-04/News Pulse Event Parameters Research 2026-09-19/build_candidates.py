import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
selected=json.loads((ROOT/'selected.json').read_text())
controlled=['InpPlacementLeadSeconds','InpEntryOffsetPrice','InpStopLossPrice','InpTrailStartR','InpTrailDistancePrice','InpForceCloseSecondsAfterEvent']
code=(ROOT/'Base.mqh').read_text()
for name in controlled:
 code,n=re.subn(r'input\s+(int|double)\s+('+name+r')\s*=',r'\1 \2=',code);assert n==1,name
helper='''double NPX_TPR=0;
int NPX_Anchor=0;
double NPX_BuyAnchor(const MqlTick &q) {if(NPX_Anchor==0)return q.ask;return iHigh(_Symbol,PERIOD_M1,NPX_Anchor==1?0:1)+(q.ask-q.bid);}
double NPX_SellAnchor(const MqlTick &q) {if(NPX_Anchor==0)return q.bid;return iLow(_Symbol,PERIOD_M1,NPX_Anchor==1?0:1);}
'''
code=code.replace('datetime g_active_event_time=0;',helper+'\ndatetime g_active_event_time=0;')
code=code.replace('tick.ask+InpEntryOffsetPrice','NPX_BuyAnchor(tick)+InpEntryOffsetPrice').replace('tick.bid-InpEntryOffsetPrice','NPX_SellAnchor(tick)-InpEntryOffsetPrice')
code=code.replace('buy_sl,0.0,ORDER_TIME_SPECIFIED','buy_sl,(NPX_TPR>0 ? AAA_Price(_Symbol,buy_entry+NPX_TPR*InpStopLossPrice):0.0),ORDER_TIME_SPECIFIED')
code=code.replace('sell_sl,0.0,ORDER_TIME_SPECIFIED','sell_sl,(NPX_TPR>0 ? AAA_Price(_Symbol,sell_entry-NPX_TPR*InpStopLossPrice):0.0),ORDER_TIME_SPECIFIED')
(ROOT/'CandidateBase.mqh').write_text(code)
for tag,mode in [('NativeFullBestV2','full'),('NativeTrainSelectedV2','train')]:
 settings='void ApplySettings(const string kind) {\n'
 for k in ('NFP','CPI','FOMC'):
  p=selected[k][mode]['params']
  settings+=f'''if(kind=="{k}") {{InpPlacementLeadSeconds={int(p[0])};NPX_Anchor={int(p[1])};InpEntryOffsetPrice={p[2]};InpStopLossPrice={p[3]};NPX_TPR={p[4]};InpTrailStartR={p[5] if p[5] else 100000};InpTrailDistancePrice={p[6]};InpForceCloseSecondsAfterEvent={int(p[7])};}}\n'''
 settings+='}\n'
 original=(ROOT/'NativeBaseline.mq5').read_text()
 start=original[:original.index('int export_file')].replace('"Base.mqh"','"CandidateBase.mqh"')
 window=original[original.index('int EventWindow()'):original.index('int OnInit()')]
 wrapper='''int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTick();}
void OnTimer(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}
'''
 (ROOT/(tag+'.mq5')).write_text(start+window+settings+wrapper)
 print('Built research-only '+tag)

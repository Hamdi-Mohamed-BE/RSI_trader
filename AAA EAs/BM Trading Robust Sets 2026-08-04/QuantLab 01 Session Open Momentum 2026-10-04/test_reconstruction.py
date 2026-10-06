"""Guard the first-idea experiment against accidentally changing unrelated production logic."""
import json,unittest
from pathlib import Path
from html.parser import HTMLParser
R=Path(__file__).resolve().parent
def signal(open_,close,ema,mode):
    direction=1 if close>ema else -1 if close<ema else 0
    if mode!=0 and direction>0 and close<=open_:return 0
    if mode==2 and direction<0 and close>=open_:return 0
    return direction
class ReconstructionTests(unittest.TestCase):
    def test_buy_body_confirmation(self):
        self.assertEqual(signal(110,105,100,0),1)
        self.assertEqual(signal(110,105,100,1),0)
        self.assertEqual(signal(110,105,100,2),0)
        self.assertEqual(signal(100,110,105,1),1)
        self.assertEqual(signal(100,110,105,2),1)
    def test_explicit_short_ambiguity(self):
        self.assertEqual(signal(90,95,100,1),-1)
        self.assertEqual(signal(90,95,100,2),0)
        self.assertEqual(signal(100,90,95,1),-1)
        self.assertEqual(signal(100,90,95,2),-1)
    def test_equal_ema_and_doji(self):
        self.assertEqual(signal(100,100,100,0),0)
        self.assertEqual(signal(100,100,95,1),0)
        self.assertEqual(signal(100,100,105,1),-1)
        self.assertEqual(signal(100,100,105,2),0)
    def test_production_core_only_declared_changes(self):
        original=(R.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5').read_text(encoding='utf-8-sig')
        derived=(R/'EA/Calyx Session Open Momentum Research.mq5').read_text(encoding='utf-8-sig')
        original=original[original.index('enum ENUM_N5_STOP_MODE'):].strip()
        derived=derived[derived.index('enum ENUM_N5_STOP_MODE'):].strip()
        expected=original.replace('if(!SignalQualityPasses(direction,rates[1],ema,previous_ema,atr)) return;',
            'if(InpSOMBodyMode!=SOM_EXISTING_CLOSE_ONLY && direction>0 && rates[1].close<=rates[1].open) return;\n'
            '   if(InpSOMBodyMode==SOM_SYMMETRIC_ASSUMPTION && direction<0 && rates[1].close>=rates[1].open) return;\n'
            '   if(!SignalQualityPasses(direction,rates[1],ema,previous_ema,atr)) return;')
        expected=expected.replace('if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;',
            'if(!DTS_InputsValid() || (int)InpSOMBodyMode<0 || (int)InpSOMBodyMode>2) return INIT_PARAMETERS_INCORRECT;')
        self.assertEqual(expected,derived)
        for include in ['SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:
            self.assertEqual((R/'EA'/include).read_bytes(),
                (R.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA'/include).read_bytes())
    def test_native_parity_passed(self):
        p=json.loads((R/'parity.json').read_text())
        self.assertTrue(p['passed']);self.assertEqual(p['positions'],10);self.assertEqual(p['net_profit'],699.59)
    def test_complete_report_assets(self):
        class Parser(HTMLParser):
            def __init__(self):super().__init__();self.links=[];self.svgs=0;self.details=0
            def handle_starttag(self,tag,attrs):
                values=dict(attrs)
                if tag=='a' and 'href' in values:self.links.append(values['href'])
                self.svgs+=tag=='svg';self.details+=tag=='details'
        parser=Parser();parser.feed((R/'Results.html').read_text(encoding='utf-8'))
        self.assertEqual(parser.svgs,12);self.assertEqual(parser.details,10)
        for link in parser.links:
            if not link.startswith('https:'):self.assertTrue((R/link).is_file(),link)
        summary=json.loads((R/'summary.json').read_text())
        self.assertEqual(len(summary),10)
        self.assertEqual({(x['window'],x['version']) for x in summary},
                         {(w,n) for w in ('1Y','3M') for n in ('CURRENT','CURRENT_NO_DI','OLD','VIDEO_LITERAL','VIDEO_SYMMETRIC')})
if __name__=='__main__':unittest.main()

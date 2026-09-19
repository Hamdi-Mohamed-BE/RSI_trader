"""Generate the user-approved full-year fitted production package, not a live install."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
NAME = 'AAA Final News Pulse Multi Asset Event EA'
SOURCE = PACKAGE/'AAA Final EAs'/NAME/(NAME+'.mq5')
SETS = PACKAGE/'Selected Portfolio Settings 2026-09-01'
SET_NAMES = {
    'XAG': '12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set',
    'BTC': '12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set',
    'EURUSD': '12D News Pulse EURUSD Event Specific - HARD 1.5 TOTAL.set',
}

def main():
    template = PACKAGE/'AAA Final EAs'/'AAA Final News Pulse XAU Event Specific EA'/'AAA Final News Pulse XAU Event Specific EA.mq5'
    code = template.read_text(encoding='utf-8-sig')
    code = code.replace('"2.16"', '"2.17"').replace('InpUseXauEventSpecific', 'InpUseAssetEventSpecific')
    code = code.replace('// XAU/GOLD only; NFP/CPI/FOMC promoted 2026-09-19', '// XAG/BTC/EURUSD full-year fitted; approved 2026-09-19')
    start = code.index('bool NP_XauEventSpecific()')
    end = code.index('string NP_KindFromComment', start)
    block = '''// Generated from the frozen selected.json full-year candidates. Hindsight optimized.
string NP_Asset()
{
   string symbol=_Symbol; StringToUpper(symbol);
   if(StringFind(symbol,"XAG")==0 || StringFind(symbol,"SILVER")==0) return "XAG";
   if(StringFind(symbol,"BTC")==0 || StringFind(symbol,"BITCOIN")==0) return "BTC";
   if(StringFind(symbol,"EURUSD")==0) return "EURUSD";
   return "";
}
int g_np_lead=30,g_np_hold=60,g_np_anchor=0;
double g_np_offset=1,g_np_stop=1,g_np_trail_start=1.5,g_np_trail_distance=1,g_np_tp=0;
void NP_ApplyEventParameters(const string kind)
{
   g_np_lead=InpPlacementLeadSeconds; g_np_hold=InpForceCloseSecondsAfterEvent;
   g_np_offset=InpEntryOffsetPrice; g_np_stop=InpStopLossPrice;
   g_np_trail_start=InpTrailStartR; g_np_trail_distance=InpTrailDistancePrice;
   g_np_tp=0; g_np_anchor=0;
   string asset=NP_Asset();
'''
    selected = {}
    for asset in SET_NAMES:
        entries = json.loads((ROOT/asset/'selected.json').read_text())
        selected[asset] = {}
        for kind in ('NFP', 'CPI', 'FOMC'):
            p = entries[kind]['full']['params_price']
            selected[asset][kind] = p
            block += (f'   if(asset=="{asset}" && kind=="{kind}") '
                      f'{{g_np_lead={int(p[0])};g_np_anchor={int(p[1])};g_np_offset={p[2]:.10f};'
                      f'g_np_stop={p[3]:.10f};g_np_tp={p[4]};g_np_trail_start={p[5]};'
                      f'g_np_trail_distance={p[6]:.10f};g_np_hold={int(p[7])};}}\n')
    block += '''}
int NP_LeadSeconds(const string kind)
{
   // Called only when no owned exposure is being managed. Event-kind parameters
   // are restored from persistent state/comments before every lifecycle action.
   NP_ApplyEventParameters(kind);
   return g_np_lead;
}
'''
    code = code[:start]+block+code[end:]
    code = code.replace('if(g_np_closed_m1)', 'if(g_np_anchor>0)')
    code = code.replace('double h=iHigh(_Symbol,PERIOD_M1,1),l=iLow(_Symbol,PERIOD_M1,1);',
                        'int shift=(g_np_anchor==1 ? 0:1);\n      double h=iHigh(_Symbol,PERIOD_M1,shift),l=iLow(_Symbol,PERIOD_M1,shift);')
    code = code.replace('closed M1 anchor unavailable', 'M1 anchor unavailable')
    code = code.replace('int OnInit()\n{', 'int OnInit()\n{\n   if(!InpUseAssetEventSpecific || NP_Asset()=="") {Print("News Pulse v2.17 requires the approved XAG, BTC or EURUSD event profile.");return INIT_PARAMETERS_INCORRECT;}')
    lines = code.splitlines()
    lines = [line for line in lines if 'if(NP_XauEventSpecific()) Print' not in line]
    code = '\n'.join(lines)+'\n'
    code = code.replace('AAA Final News Pulse v2.16 loaded', 'AAA Final News Pulse v2.17 FULL-YEAR FITTED loaded')
    code = code.replace('event-specific XAU overrides when enabled', 'asset/event-specific overrides')
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(code, encoding='utf-8')
    (SOURCE.parent/'EVENT PARAMETERS.json').write_text(json.dumps(selected, indent=2), encoding='utf-8')
    for asset, name in SET_NAMES.items():
        # Frozen research baseline avoids taking unrelated/stale runtime inputs.
        settings = json.loads((ROOT/asset/'baseline-settings.json').read_text())
        settings.update(InpUseAssetEventSpecific='true', InpEnableTrading='true',
                        InpEnableBuySide='true', InpEnableSellSide='true',
                        InpAdaptivePortfolioControls='false', InpRiskPercent='0.75',
                        InpUseDynamicTrailingSL='false', InpResearchSession='0',
                        InpUseMarkovRegimeFilter='false')
        (SETS/name).write_text('\n'.join(k+'='+v for k,v in settings.items())+'\n', encoding='utf-8')
    dest = ROOT/'Deployment';dest.mkdir(exist_ok=True)
    (dest/'APPROVED.json').write_text(json.dumps(dict(selection='full', approved='2026-09-19',
        source=str(SOURCE.relative_to(PACKAGE)), settings=SET_NAMES, params=selected,
        risk_per_side_percent=.75, both_sides_retained=True,
        warning='In-sample full-year fit; not expected returns or a realized loss cap. XAU unchanged.'), indent=2))
    print('Generated source and three selected SETs. No terminal attached or restarted.')

if __name__ == '__main__':main()

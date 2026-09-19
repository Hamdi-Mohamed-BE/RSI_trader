"""Public metadata for the explicitly approved 2026-09-19 full-year fit."""
import json
from pathlib import Path

MULTI_PROFILE = 'multi-event-full-2026-09-19'
MULTI_SLUGS = frozenset({'news-pulse-xag', 'news-pulse-btc', 'news-pulse-eurusd'})
PACKAGE = Path(__file__).resolve().parents[2]/'BM Trading Robust Sets 2026-08-04'
PARAMETERS_PATH = PACKAGE/'AAA Final EAs'/'AAA Final News Pulse Multi Asset Event EA'/'EVENT PARAMETERS.json'

def event_parameters(asset):
    return json.loads(PARAMETERS_PATH.read_text(encoding='utf-8'))[asset]

def event_profile_meta(asset):
    params=event_parameters(asset)
    symbol={'XAG':'XAGUSD','BTC':'BTCUSD','EURUSD':'EURUSD'}[asset]
    def distance(value):
        return f'{value/.0001:g} pips' if asset=='EURUSD' else f'${value:g} price units'
    anchors={0:'current Ask/Bid',1:'active M1 high/low at placement',2:'previous closed M1 high/low'}
    logic=[]
    for event,p in params.items():
        trail='Trailing off' if p[5]==0 else f'Trail from {p[5]:g}R with {distance(p[6])} distance'
        tp='no TP' if p[4]==0 else f'{p[4]:g}R TP'
        logic.append({'title':f'{event}: T-{p[0]:g}s placement',
                      'detail':f'Anchor: {anchors[int(p[1])]}; entry offset {distance(p[2])}; initial SL {distance(p[3])}; {tp}. {trail}. Delete unfilled orders and close remaining exposure at T+{p[7]:g}s.'})
    logic += [
        {'title':'Primary high-impact USD events only','detail':'Native MT5 calendar accepts primary CPI/Core CPI, non-private NFP and FOMC decisions/statements. Cleveland Median CPI and secondary releases remain excluded. Broker calendar/quote time is used, not VPS local time.'},
        {'title':'Keep both pending directions','detail':'Both sides are retained, not OCO. Each targets 0.75% equity risk before costs and lot rounding. Recommended Adaptive does not block or taper News Pulse. Fresh quotes, symbol history, broker order and margin constraints still apply.'},
        {'title':'Recover the active event after restart','detail':'Account/symbol/magic state and order comments restore the event family before applying its trailing and timed exit. Do not change a profile with owned exposure open.'},
    ]
    return dict(strategy='Event-specific two-sided news breakout',
                tagline=f'{symbol}: separate NFP, CPI and FOMC settings; both pending directions retained.',
                description='User-approved full-year optimized configuration, selected on 19 September 2025–19 September 2026. '+ ' '.join(x['title']+'. '+x['detail'] for x in logic[:3]),
                session='NFP, CPI and FOMC',logic_audit='Source-code verified',
                logic_audit_note='Production v2.17. Native production/research parity is checked before publishing independent website-period replays. Full-year parameter fitting overlaps the displayed history; this is not untouched validation or a forecast.',
                logic=logic,risk_note='HINDSIGHT-OPTIMIZED. Very tight stops can create large positions and losses far above 0.75% per side during gaps or adverse fills. Four concurrent News Pulse charts plan 6% combined before costs/rounding; Gold News V9 is additional exposure. Not demonstrated prop-firm-safe. Historical spread, recorded commission/swap and tester execution assumptions are disclosed by period.',
                price=549,accent='yellow',featured=True)

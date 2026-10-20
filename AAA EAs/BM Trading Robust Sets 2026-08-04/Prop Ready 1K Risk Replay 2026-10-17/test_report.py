"""Report-only fixtures: cash dates, escaping, evidence links, and JS switching."""
import copy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import report


def epoch(iso):
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp())


def fixture():
    t0, op, cl, end = [epoch(s) for s in ('2026-08-17', '2026-08-18T10:00:00',
        '2026-08-19T10:00:00', '2026-10-16T23:59:59')]
    plan = dict(start_utc='2026-08-17T00:00:00+00:00',
        end_exclusive_utc='2026-10-17T00:00:00+00:00', initial_balance=1000,
        priority=['xau-rsi-vwap', 'nasdaq-5m-candle-momentum'], reference_risk_cap=.005,
        limitations=['Exposed dates, not an independent future test.'])
    trade = dict(id='xau-rsi-vwap|1', ea='xau-rsi-vwap', symbol='XAUUSD',
        side='buy', op=op, cl=cl, open_price=2000, close_price=2002,
        lots=.01, sl=1995, tp=2002.5, risk=5, gross=2, commission=-.1,
        swap=-.2, entry_cash=-.1, exit_cash=1.8, net=1.7, balance=1001.7)
    result = dict(scenario=dict(id='fixed_5', label='Fixed $5', value=5, mode='fixed'),
        stress=False, metrics=dict(ending_balance=1001.7, ending_sampled_equity=1001.7,
            return_pct=.17, trades=1, win_rate_pct=100, profit_factor=None,
            profit_factor_status='no_losing_trades', net_profit=1.7,
            max_closed_dd_cash=.1, max_closed_dd_pct=.01,
            max_sampled_equity_dd_cash=3, max_sampled_equity_dd_pct=.3,
            max_daily_closed_dd_cash=.1, max_daily_sampled_equity_dd_cash=3,
            max_daily_anchor_equity_loss=3, max_win_streak=1, max_loss_streak=0,
            average_win=1.7, average_loss=None, largest_win=1.7, largest_loss=None,
            daily_closed_sharpe=1.234, open_positions=0, hard_loss_latch=False,
            average_trades_per_calendar_day=1/61, average_trades_per_weekday=1/45,
            counts={'opened':1,'closed':1,'minimum_lot_over_budget':1}),
        per_ea={'xau-rsi-vwap':{'candidates':1,'opened':1,'closed':1},
            'nasdaq-5m-candle-momentum':{'candidates':1,'minimum_lot_over_budget':1}},
        trades=[trade], decisions=[dict(id=trade['id'],ea=trade['ea'],epoch=op,
            equity=1000,budget=5,source_volume_ceiling=.1,volume=.01,
            stop_risk=5,minimum_lot_risk=5,reason='opened'),
            dict(id='nasdaq|2',ea='nasdaq-5m-candle-momentum',epoch=op+10,
            equity=999.9,budget=5,source_volume_ceiling=.2,volume=0,
            stop_risk=0,minimum_lot_risk=20,reason='minimum_lot_over_budget')],
        curve=[dict(epoch=t0,balance=1000,equity=1000),
            dict(epoch=op,balance=999.9,equity=999.9),
            dict(epoch=op+300,balance=999.9,equity=997),
            dict(epoch=cl,balance=1001.7,equity=1001.7),
            dict(epoch=end,balance=1001.7,equity=1001.7)],
        mark_quality={'owned_marks':1,'missing_open_swap_marks':0})
    second = copy.deepcopy(result)
    second['scenario'] = dict(id='percent_1', label='Dynamic 1% (still capped)', mode='percent',value=1)
    second['stress'] = True
    second['metrics']['ending_balance'] = 1000.70
    second['metrics']['return_pct'] = .07
    second['curve'][-1]['balance'] = 1000.70
    return dict(plan=plan, results=[result,second],coverage=[dict(ea='xau-rsi-vwap',candidates=1,
        native={'history_quality':'100% real ticks'},end_censored=0,owned_marks=1,
        first_epoch=t0,last_epoch=end)],broker=dict(broker='Exness',server='Exness-MT5Trial15',
        currency='USD',leverage=2000,symbols={'XAUUSD':dict(volume_min=.01,volume_step=.01,
            trade_contract_size=100,quote_spread=.2,buy_margin_one_lot=200,
            sell_margin_one_lot=200,quote_epoch=end)}),generated_at_utc='2026-10-17T15:00:00+00:00')


class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs = [], []
        self.script_type = None
        self.code, self.payload = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.hrefs.append(attrs.get('href', ''))
        if tag == 'script':
            self.script_type = attrs.get('type','javascript')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.script_type = None

    def handle_data(self, data):
        if self.script_type == 'application/json':
            self.payload.append(data)
        elif self.script_type == 'javascript':
            self.code.append(data)


class ReportTests(unittest.TestCase):
    def test_numeric_format(self):
        self.assertEqual(report.cash(-2.35), '−$2.35')
        self.assertEqual(report.cash(2.35,True), '+$2.35')
        self.assertEqual(report.percent(.17,True), '+0.17%')
        self.assertEqual(report.number(None), '—')
        self.assertEqual(report.number(float('nan')), '—')
        self.assertEqual(report.number(float('inf')), '—')

    def test_empty_report_rejected(self):
        data=fixture();data['results']=[]
        with self.assertRaises(ValueError):
            report.render(data)

    def test_numeric_render_and_default(self):
        html=report.render(fixture())
        self.assertIn('$1,001.70',html)
        self.assertIn('+0.17%',html)
        self.assertIn('No losses',html)
        self.assertIn('1.23',html)
        self.assertIn('value="fixed_5" selected',html)
        self.assertNotIn('@@',html)

    def test_no_trade_profile_ea_still_visible(self):
        data=fixture();data['plan']['priority'].append('untriggered-test-ea')
        html=report.per_ea_table(data['results'][0],data['plan'])
        self.assertIn('untriggered test ea',html)
        self.assertIn('No matching records.',report.table(['a'],[]))

    def test_pf_no_loss_not_zero_or_infinity(self):
        self.assertEqual(report.pf({'profit_factor':None,'profit_factor_status':'no_losing_trades'}),'No losses')
        self.assertEqual(report.pf({'profit_factor':None,'profit_factor_status':'no_trades'}),'—')
        self.assertEqual(report.pf({'profit_factor':1.238}),'1.24')

    def test_day_cash_not_allocated_entirely_to_exit(self):
        data=fixture();days,months=report.cash_periods(data['results'][0],data['plan'])
        bydate={d['date']:d for d in days}
        self.assertAlmostEqual(bydate['2026-08-18']['net_cash'],-.1)
        self.assertAlmostEqual(bydate['2026-08-19']['net_cash'],1.8)
        self.assertEqual(bydate['2026-08-18']['entries'],1)
        self.assertEqual(bydate['2026-08-19']['closes'],1)
        self.assertEqual(len(days),62)
        self.assertEqual([m['month'] for m in months],['2026-08','2026-09','2026-10'])
        self.assertTrue(days[0]['partial']);self.assertTrue(days[-1]['partial'])
        self.assertAlmostEqual(sum(d['net_cash'] for d in days),1.7)
        self.assertAlmostEqual(months[-1]['end_balance'],1001.7)

    def test_same_second_cash_events_reconcile(self):
        data=fixture();r=data['results'][0];e=r['curve'][1]['epoch']
        r['curve'][2:2]=[dict(epoch=e,balance=999.7,equity=999.7)]
        days,_=report.cash_periods(r,data['plan'])
        self.assertAlmostEqual(sum(d['net_cash'] for d in days),1.7)

    def test_capital_requirement_is_not_current_minlot_margin(self):
        data=fixture();table=report.per_ea_table(data['results'][0],data['plan'])
        self.assertIn('$4,000.00 / $4,000.00 / $4,000.00',table)
        self.assertIn('$1,000.00 / $1,000.00 / $1,000.00',table)

    def test_cost_fallback_and_sharpe_missing(self):
        data=fixture();data['results'][0]['metrics'].pop('daily_closed_sharpe')
        html=report.render(data)
        self.assertIn('UTC daily closed-cash-return Sharpe',html)
        self.assertIn('Extra-cost sensitivity',html)
        self.assertIn('one additional observed snapshot spread',html)

    def test_no_fabricated_future_profit_claim(self):
        html=report.render(fixture())
        for phrase in ('not a native simultaneous portfolio','Neither view is a verified native backtest',
            'reference does not automatically rebase','not tick-accurate worst losses',
            'alternative signals cannot be invented','two exposed months',
            'not a certification of historical financing','does not support a reliable 2%-per-day'):
            self.assertTrue(phrase in html,phrase)

    def test_feed_caveat_and_optional_spotcheck(self):
        data=fixture();data['feed_spot_checks']={'USTEC':dict(native_spread=0,current_spread=.78,
            full_feed_parity_proven=False)}
        html=report.render(data)
        self.assertIn('Source-account recorded costs',html)
        self.assertIn('Raw-like pricing',html)
        self.assertIn('zero bid–ask spread plus recorded commissions',html)
        self.assertIn('not exact replacement of Raw pricing with Pro pricing',html)
        self.assertIn('full_feed_parity_proven',html)

    def test_new_sharpe_key_and_no_curve_are_not_imputed(self):
        data=fixture();r=data['results'][0]
        r['metrics'].pop('daily_closed_sharpe');r['metrics']['daily_closed_return_sharpe']=2.456
        self.assertIn('2.46',report.metrics_html(r))
        r['curve']=[]
        self.assertEqual(report.cash_periods(r,data['plan']),([],[]))

    def test_html_escaping_all_data_tables(self):
        data=fixture();evil='</script><img src=x onerror=alert(1)>'
        data['results'][0]['scenario']['label']=evil
        data['results'][0]['trades'][0]['symbol']=evil
        data['plan']['limitations']=[evil]
        html=report.render(data)
        self.assertNotIn(evil,html)
        self.assertIn('&lt;/script&gt;&lt;img',html)
        self.assertIn('\\u003c/script\\u003e',html)

    def test_script_json_round_trip(self):
        value={'x':'</script><!--\u2028\u2029&>','number':1.2}
        encoded=report.script_json(value)
        self.assertNotIn('<',encoded);self.assertNotIn('&',encoded)
        self.assertEqual(json.loads(encoded),value)

    def test_local_evidence_links_exist(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('RESULTS.json','PLAN.json','BROKER.json'):
                (root/name).write_text('{}',encoding='utf-8')
            html=report.render(fixture(),root)
            parsed=Parse();parsed.feed(html)
            local=[u for u in parsed.hrefs if not u.startswith(('http:','https:','#'))]
            self.assertEqual(set(local),{'RESULTS.json','PLAN.json','BROKER.json'})
            self.assertTrue(all((root/u).is_file() for u in local))
            self.assertNotIn('private',report.evidence_links(root))

    def test_unique_ids_and_all_static_js_targets(self):
        parsed=Parse();parsed.feed(report.render(fixture()))
        self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
        code=''.join(parsed.code)
        for target in re.findall(r"getElementById\('([^']+)'\)",code):
            self.assertIn(target,parsed.ids)
        self.assertEqual(len(json.loads(''.join(parsed.payload))['views']),2)

    def test_reduced_curve_preserves_extrema(self):
        points=[dict(epoch=i,balance=1000+(i%77),equity=1000-(i%13)) for i in range(10000)]
        reduced=report.reduced_curve(points,100)
        self.assertLessEqual(len(reduced),102)
        self.assertEqual(reduced[0],points[0]);self.assertEqual(reduced[-1],points[-1])
        self.assertEqual(max(p['balance'] for p in reduced),max(p['balance'] for p in points))
        self.assertEqual(min(p['equity'] for p in reduced),min(p['equity'] for p in points))
        self.assertEqual([p['epoch'] for p in reduced],sorted(p['epoch'] for p in reduced))

    @unittest.skipUnless(shutil.which('node'),'Node unavailable for sandboxed DOM fixture')
    def test_javascript_executes_and_switches_scenarios(self):
        parsed=Parse();parsed.feed(report.render(fixture()))
        payload=json.loads(''.join(parsed.payload))
        wrapper=r'''
const assert=require('node:assert/strict');
class Element{constructor(){this.value='';this.children=[];this.events={};this.textContent='';this.innerHTML='';}setAttribute(k,v){this[k]=v;}appendChild(x){this.children.push(x);}replaceChildren(){this.children=[];}getBoundingClientRect(){return{width:340};}addEventListener(k,f){this.events[k]=f;}}
const elements=Object.fromEntries(IDS.map(x=>[x,new Element()]));
elements['replay-data'].textContent=JSON.stringify(PAYLOAD);elements.scenario.value='fixed_5';elements.cost.value='0';
global.document={getElementById:id=>{assert.ok(elements[id],id);return elements[id];},createElementNS:()=>new Element()};
global.ResizeObserver=class{constructor(f){this.f=f;}observe(){this.f();}};
CODE
assert.ok(elements['cash-chart'].children.length>5);
elements.scenario.value='percent_1';elements.cost.value='1';elements.scenario.events.change();
assert.match(elements['selected-state'].textContent,/Dynamic 1%.*extra-cost sensitivity/);
assert.match(elements.metrics.innerHTML,/1,000.70/);
assert.match(elements['chart-note'].textContent,/recorded path observations/);
elements.cost.value='0';elements.cost.events.change();
assert.match(elements['selected-state'].textContent,/No completed outcome/);
process.stdout.write('JS selector, chart, and empty-combination fixture passed');
'''
        wrapper=wrapper.replace('IDS',json.dumps(parsed.ids)).replace('PAYLOAD',json.dumps(payload)).replace('CODE',''.join(parsed.code))
        run=subprocess.run([shutil.which('node'),'-e',wrapper],text=True,capture_output=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)
        self.assertIn('fixture passed',run.stdout)


@unittest.skipUnless((Path(__file__).parent/'RESULTS.json').is_file(),'Frozen completed outcomes not yet available')
class CompletedResultReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parent
        cls.data=report.read(cls.root/'RESULTS.json')

    def test_all_completed_scenario_cash_days_and_months_reconcile(self):
        self.assertEqual(len(self.data['results']),10)
        for r in self.data['results']:
            with self.subTest(scenario=r['scenario']['id'],stress=r['stress']):
                days,months=report.cash_periods(r,self.data['plan'])
                expected=r['metrics']['ending_balance']-self.data['plan']['initial_balance']
                self.assertAlmostEqual(sum(d['net_cash'] for d in days),expected,places=7)
                self.assertAlmostEqual(sum(m['net_cash'] for m in months),expected,places=7)
                self.assertAlmostEqual(months[-1]['end_balance'],r['metrics']['ending_balance'],places=7)
                self.assertEqual(sum(d['closes'] for d in days),r['metrics']['trades'])
                self.assertEqual(sum(d['entries'] for d in days),sum(d['reason']=='opened' for d in r['decisions']))
                self.assertEqual(len(days),62)

    def test_real_default_and_tiny_denominator_warning(self):
        html=report.render(self.data,self.root)
        self.assertTrue('2 of 9 EAs admitted an order' in html)
        self.assertTrue('79 of 93 observed source entries' in html)
        self.assertTrue('only 3 closed positions and $0.07 total recorded losses' in html)
        self.assertTrue('recommended winner' in html)
        self.assertTrue('value="fixed_5" selected' in html)
        self.assertNotIn('@@',html)

    def test_actual_html_evidence_and_payload(self):
        html=report.render(self.data,self.root)
        p=Parse();p.feed(html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        payload=json.loads(''.join(p.payload))
        self.assertEqual(len(payload['views']),10)
        self.assertEqual(payload['views'][payload['default']]['scenario']['id'],'fixed_5')
        for href in p.hrefs:
            if not href.startswith(('https:','http:','#')):
                self.assertTrue((self.root/href.replace('%20',' ')).is_file(),href)
        self.assertTrue(all('100% real ticks'==c['native']['history_quality'] for c in self.data['coverage']))

    def test_rendered_native_source_counts_not_portfolio_counts(self):
        for r in self.data['results']:
            self.assertEqual(len(r['decisions']),93)
            self.assertEqual(sum(r['per_ea'].get(slug,{}).get('candidates',0)
                for slug in self.data['plan']['priority']),93)
            self.assertEqual(sum(r['per_ea'].get(slug,{}).get('closed',0)
                for slug in self.data['plan']['priority']),len(r['trades']))


if __name__=='__main__':
    unittest.main()

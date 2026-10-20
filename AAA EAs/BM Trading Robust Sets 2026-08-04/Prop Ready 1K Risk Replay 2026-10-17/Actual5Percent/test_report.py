"""Actual-risk report fixtures; never run a tester or mutate frozen inputs."""
import copy
from datetime import datetime,timezone
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('actual_five_percent_report',ROOT/'report.py')
report=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def fixture():
    def ep(s):
        return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
    start=ep('2026-08-17');op=ep('2026-09-01T10:00:00');cl=op+600;last=ep('2026-10-16T23:59:59')
    plan=dict(initial_balance=1000,start_utc='2026-08-17T00:00:00+00:00',
        end_exclusive_utc='2026-10-17T00:00:00+00:00',priority=['xau-rsi-vwap','nasdaq-5m-candle-momentum'])
    trade=dict(id='a',ea='xau-rsi-vwap',symbol='XAUUSD',side='buy',op=op,cl=cl,lots=.1,
        risk=50,entry_cash=-1,exit_cash=51,net=50,gross=52,commission=-2,swap=0,balance=1050)
    result=dict(scenario=dict(id='fixed50',label='Fixed $50',mode='fixed',value=50),stress=False,
        metrics=dict(ending_balance=1048,ending_sampled_equity=1100,return_pct=4.8,
            ending_equity_return_pct=10,trades=1,profit_factor_status='no_losing_trades',profit_factor=None,
            win_rate_pct=100,max_closed_dd_pct=.2,max_sampled_equity_dd_pct=1.2,
            max_daily_sampled_equity_dd_cash=12,max_win_streak=1,max_loss_streak=0,
            daily_closed_return_sharpe=1.2,open_positions=1,hard_loss_latch=False),
        trades=[trade],decisions=[dict(id='a',ea='xau-rsi-vwap',epoch=op,equity=1000,budget=50,
            reason='opened',minimum_lot_risk=5,volume=.1,stop_risk=50),
            dict(id='b',ea='nasdaq-5m-candle-momentum',epoch=cl+300,equity=1050,budget=50,
            reason='opened',minimum_lot_risk=9,volume=.2,stop_risk=49)],
        per_ea={'xau-rsi-vwap':dict(candidates=1,opened=1,closed=1),
                'nasdaq-5m-candle-momentum':dict(candidates=1,opened=1)},
        curve=[dict(epoch=start,balance=1000,equity=1000),
               dict(epoch=op,balance=999,equity=999),dict(epoch=cl,balance=1050,equity=1050),
               dict(epoch=cl+300,balance=1048,equity=1048),
               dict(epoch=last,balance=1048,equity=1100)],
        mark_quality={'owned_marks':3,'missing_open_swap_marks':3})
    results=[]
    for stress in (False,True):
        for mode in ('fixed','percent'):
            r=copy.deepcopy(result);r['stress']=stress;r['scenario']['mode']=mode
            r['scenario']['id']=mode+str(stress);r['scenario']['label']='Fixed $50' if mode=='fixed' else 'Dynamic 5%'
            results.append(r)
    return dict(plan=plan,results=results,controls=[copy.deepcopy(result)],guard_policy={'daily_loss':.1},
        generated_at_utc='2026-10-17T18:00:00+00:00')


class Parse(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.hrefs=[];self.paths=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='a':self.hrefs.append(a.get('href',''))
        if tag=='path':self.paths.append(a.get('d',''))


class ActualReportTests(unittest.TestCase):
    def test_refuses_empty_outcomes(self):
        d=fixture();d['results']=[]
        with self.assertRaises(ValueError):report.render(d)

    def test_actual_allocation_not_capped(self):
        html=report.render(fixture())
        for phrase in ('fixed $50','5% of current sampled equity','bypassed only in this separate research model',
            '20% account loss takes a 25% gain','Existing positions are not automatically liquidated',
            'not a new simultaneous native test','not exact Pro repricing'):
            self.assertTrue(phrase in html,phrase)
        self.assertNotIn('@@',html)

    def test_distinct_cash_equity_and_closed_pf(self):
        html=report.render(fixture())
        for phrase in ('$1,048.00','$1,100.00','+4.80%','+10.00%',
            'closed positions only','not banked','No losses'):
            self.assertTrue(phrase in html,phrase)

    def test_open_entry_fees_reconcile_daily_and_monthly(self):
        data=fixture()
        for result in data['results']:
            ds,ms=report.base.cash_periods(result,data['plan'])
            self.assertAlmostEqual(sum(d['net_cash'] for d in ds),48)
            self.assertAlmostEqual(sum(m['net_cash'] for m in ms),48)
            self.assertNotEqual(sum(t['net'] for t in result['trades']),48)
            html=report.monthly(result,data['plan'])[0]
            self.assertTrue('+$48.00' in html)

    def test_open_exposure_fallback_not_closed(self):
        r=fixture()['results'][0]
        html=report.still_open(r)
        self.assertTrue('1 open position(s)' in html)
        self.assertTrue('+$52.00' in html)
        self.assertTrue('Nasdaq 5M candle momentum' in html)
        self.assertTrue('Individual final marks were not supplied' in html)

    def test_explicit_open_exposure_details(self):
        r=fixture()['results'][0]
        r['open_positions']=[dict(ea='nasdaq-5m-candle-momentum',symbol='USTEC',op=1,lots=.2,risk=49,floating=52)]
        html=report.still_open(r)
        self.assertTrue('Final owned sampled floating P&amp;L' in html)
        self.assertTrue('0.200' in html)

    def test_per_ea_actual_risk_not_reference_half_percent(self):
        data=fixture();html=report.per_ea(data['results'][0],data['plan'])
        self.assertTrue('$50.00 / $50.00 / $50.00' in html)
        self.assertTrue('5.00%' in html)
        self.assertNotIn('0.5% cap',html)

    def test_chart_both_cost_panels_and_non_overlapping_html_axes(self):
        html=report.render(fixture());p=Parse();p.feed(html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertEqual(len(p.paths),4)
        self.assertTrue(all('nan' not in d.lower() and 'inf' not in d.lower() for d in p.paths))
        for d in p.paths:
            for x,y in re.findall(r'[ML]([\d.]+),([\d.]+)',d):
                self.assertTrue(0<=float(x)<=1000)
                self.assertTrue(0<=float(y)<=220)
        self.assertTrue('USD sampled equity and UTC dates' in html)

    def test_string_escaping(self):
        data=fixture();evil='<script>alert("x")</script>'
        data['results'][0]['scenario']['label']=evil
        data['guard_policy']['x']=evil
        html=report.render(data)
        self.assertNotIn(evil,html)
        self.assertTrue('&lt;script&gt;' in html)

    def test_evidence_only_existing_public_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'child';root.mkdir()
            (root/'RESULTS.json').write_text('{}',encoding='utf-8')
            (root.parent/'INPUTS.json').write_text('{}',encoding='utf-8')
            html=report.evidence(root);p=Parse();p.feed(html)
            self.assertEqual(set(p.hrefs),{'RESULTS.json','../INPUTS.json'})
            self.assertTrue(all((root/s).is_file() for s in p.hrefs))

    def test_empty_chart_not_fabricated(self):
        self.assertEqual(report.chart([],False),'<p>No matching recorded path.</p>')

    def test_child_plan_schema_and_ten_row_split(self):
        data=fixture();p=data['plan'];p['window_utc']=[p.pop('start_utc'),p.pop('end_exclusive_utc')]
        for r in data['results']:r['scenario']['guard_policy']='research_10daily_20total'
        control=copy.deepcopy(data['controls'][0]);control['scenario']['guard_policy']='current'
        data['results'].append(control);data['controls']=[]
        self.assertEqual(len(report.split_results(data)[0]),4)
        self.assertEqual(len(report.split_results(data)[1]),1)
        html=report.render(data)
        self.assertTrue('2026-08-17T00:00:00+00:00' in html)
        self.assertTrue('Last admitted entry UTC' in html)


@unittest.skipUnless((ROOT/'RESULTS.json').is_file(),'Waiting for frozen actual-risk outcomes')
class CompletedResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=report.load(ROOT/'RESULTS.json')

    def test_all_actual_risk_cash_dates_reconcile(self):
        primary,controls=report.split_results(self.data)
        self.assertEqual(len(primary),4)
        self.assertEqual(len(controls),6)
        plan=report.normalized_plan(self.data)
        for r in primary+controls:
            with self.subTest(label=report.title(r),stress=r.get('stress')):
                days,months=report.base.cash_periods(r,plan)
                expected=r['metrics']['ending_balance']-self.data['plan'].get('initial_balance',1000)
                self.assertAlmostEqual(sum(d['net_cash'] for d in days),expected,places=7)
                self.assertAlmostEqual(sum(m['net_cash'] for m in months),expected,places=7)
                self.assertEqual(sum(d['closes'] for d in days),len(r['trades']))
                self.assertEqual(sum(d['entries'] for d in days),report.entries(r))

    def test_real_risk_loss_and_changed_stress_path_warning(self):
        html=report.render(self.data,ROOT)
        for phrase in ('Both source-cost 5% approaches lost money',
            'Not a paired-trade cost comparison','Last admitted entry UTC',
            '$828.55','$818.11','not a 20% peak-to-trough drawdown cap'):
            self.assertTrue(phrase in html,phrase)

    def test_actual_render_has_all_primary_views_and_public_links(self):
        html=report.render(self.data,ROOT);p=Parse();p.feed(html)
        self.assertEqual(len([i for i in p.ids if i.startswith('view-')]),4)
        self.assertEqual(len(p.paths),4)
        self.assertNotIn('@@',html)
        for href in p.hrefs:
            if not href.startswith(('http:','https:','#')):
                self.assertTrue((ROOT/href.replace('%20',' ')).is_file(),href)


if __name__=='__main__':unittest.main()

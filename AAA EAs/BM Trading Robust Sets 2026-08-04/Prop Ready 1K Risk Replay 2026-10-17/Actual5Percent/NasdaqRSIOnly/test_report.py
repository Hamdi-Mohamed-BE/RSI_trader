"""Two-EA report only: never alters earlier frozen studies or source inputs."""
import copy
from datetime import datetime,timezone
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nasdaq_rsi_report_under_test',ROOT/'report.py')
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)


def fixture():
    def epoch(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
    first=epoch('2026-08-17');op=epoch('2026-09-01T12:00:00');last=epoch('2026-10-16T23:59:59')
    plan=dict(window_utc=['2026-08-17T00:00:00+00:00','2026-10-17T00:00:00+00:00'],
        initial_balance=1000,priority=list(report.SLUGS),signal_settings={'Nasdaq_DI':'ON unchanged'})
    r=dict(scenario=dict(id='fixed50',label='True fixed $50',mode='fixed',value=50,
            guard_policy='research_10daily_20total'),stress=False,
        metrics=dict(trades=1,ending_balance=1048,ending_sampled_equity=1100,return_pct=4.8,
            ending_equity_return_pct=10,open_positions=1,profit_factor=None,
            profit_factor_status='no_losing_trades',win_rate_pct=100,max_closed_dd_pct=.2,
            max_sampled_equity_dd_pct=2,max_daily_sampled_equity_dd_cash=20,
            max_win_streak=1,max_loss_streak=0,daily_closed_return_sharpe=1.2,hard_loss_latch=False),
        trades=[dict(id='rsi|1',ea=report.SLUGS[0],symbol='XAUUSD',side='buy',op=op,cl=op+300,
            lots=.1,risk=50,entry_cash=-1,exit_cash=51,net=50,gross=52,commission=-2,swap=0,balance=1050)],
        decisions=[dict(id='rsi|1',ea=report.SLUGS[0],epoch=op,equity=1000,budget=50,
                reason='opened',volume=.1,stop_risk=50,minimum_lot_risk=5),
            dict(id='nq|1',ea=report.SLUGS[1],epoch=op+600,equity=1050,budget=50,
                reason='opened',volume=.2,stop_risk=49,minimum_lot_risk=9)],
        per_ea={report.SLUGS[0]:dict(candidates=1,opened=1,closed=1),report.SLUGS[1]:dict(candidates=1,opened=1)},
        curve=[dict(epoch=first,balance=1000,equity=1000),dict(epoch=op,balance=999,equity=999),
            dict(epoch=op+300,balance=1050,equity=1050),dict(epoch=op+600,balance=1048,equity=1048),
            dict(epoch=last,balance=1048,equity=1100)],
        open_positions=[dict(id='nq|1',ea=report.SLUGS[1],op=op+600,lots=.2,initial_risk=49,
            paid_entry_cash=-2,mark_epoch=last-600,sampled_floating=52)],mark_quality={'owned_marks':3})
    results=[]
    for stress in (False,True):
        for mode in ('fixed','percent'):
            value=copy.deepcopy(r);value['stress']=stress;value['scenario']['mode']=mode
            value['scenario']['id']='fixed50' if mode=='fixed' else 'compound5'
            value['scenario']['label']='True fixed $50' if mode=='fixed' else 'True 5% current equity'
            results.append(value)
    data=dict(plan=plan,results=results,coverage=[dict(ea=s) for s in report.SLUGS])
    reference=copy.deepcopy(data)
    for old in reference['results']:
        old['metrics']['ending_balance']=900;old['metrics']['return_pct']=-10;old['metrics']['trades']=10
    return data,reference


class Parse(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.hrefs=[];self.paths=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='a':self.hrefs.append(a.get('href',''))
        if tag=='path':self.paths.append(a.get('d',''))


class TwoEAReportTests(unittest.TestCase):
    def test_exact_membership_required(self):
        data,old=fixture();data['plan']['priority'].append('unrelated-ea')
        with self.assertRaises(ValueError):report.render(data,old)

    def test_no_empty_outcome_report(self):
        data,old=fixture();data['results']=[]
        with self.assertRaises(ValueError):report.render(data,old)

    def test_focused_copy_di_and_replay_before_admission(self):
        data,old=fixture();html=report.render(data,old)
        for phrase in ('DI filter stays ON','Candidates are filtered',
            'before','retaining RSI’s priority ahead of Nasdaq','not the old portfolio ledger minus',
            'not a new out-of-sample test','No fresh strategy optimization'):
            self.assertTrue(phrase in html,phrase)
        for phrase in ('93 standalone','all five included ORBs','same nine strategies'):
            self.assertFalse(phrase in html,phrase)
        self.assertNotIn('@@',html)

    def test_nine_ea_comparison_matches_same_policy_and_cost(self):
        data,old=fixture();html=report.comparison(data['results'],report.reference_results(old))
        self.assertTrue('$1,048.00' in html)
        self.assertTrue('$900.00' in html)
        self.assertTrue('+14.80 pp' in html)
        self.assertEqual(html.count('<tbody>'),1)
        self.assertEqual(html.count('<tr>'),5)

    def test_missing_reference_not_substituted(self):
        data,_=fixture();html=report.comparison(data['results'],[])
        self.assertTrue('—' in html)
        self.assertFalse('$900.00' in html)

    def test_open_fee_and_last_mark_timestamp_explicit(self):
        data,_=fixture();plan=report.prior.normalized_plan(data)
        html=report.open_exposure(data['results'][0],plan)
        for phrase in ('1 position(s) still open','+$52.00','−$2.00',
            '2026-10-16 23:49:59','600','not a fresh quote','No artificial tester-end close'):
            self.assertTrue(phrase in html,phrase)

    def test_cash_vs_equity_and_closed_pf_not_conflated(self):
        data,old=fixture();html=report.render(data,old)
        for phrase in ('$1,048.00','$1,100.00','+4.80%','+10.00%','closed positions only',
            'unbanked open P&amp;L','Paid entry charges'):
            self.assertTrue(phrase in html,phrase)
        plan=report.prior.normalized_plan(data)
        for r in data['results']:
            days,months=report.prior.base.cash_periods(r,plan)
            self.assertAlmostEqual(sum(d['net_cash'] for d in days),48)
            self.assertAlmostEqual(sum(m['net_cash'] for m in months),48)
            self.assertNotEqual(sum(t['net'] for t in r['trades']),48)

    def test_unique_ids_two_charts_and_four_primary_views(self):
        data,old=fixture();p=Parse();p.feed(report.render(data,old))
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertEqual(len(p.paths),4)
        self.assertEqual(len([x for x in p.ids if x.startswith('view-')]),4)

    def test_escaped_values(self):
        data,old=fixture();evil='<script>alert(1)</script>'
        data['results'][0]['scenario']['label']=evil
        html=report.render(data,old)
        self.assertNotIn(evil,html)
        self.assertTrue('&lt;script&gt;' in html)

    def test_existing_relative_evidence_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'parent'/'child';root.mkdir(parents=True)
            for file in (root/'RESULTS.json',root.parent/'RESULTS.json',root.parent.parent/'BROKER.json'):
                file.write_text('{}',encoding='utf-8')
            p=Parse();p.feed(report.evidence(root))
            self.assertEqual(set(p.hrefs),{'RESULTS.json','../RESULTS.json','../../BROKER.json'})
            self.assertTrue(all((root/x).is_file() for x in p.hrefs))


@unittest.skipUnless((ROOT/'RESULTS.json').is_file(),'Awaiting frozen two-EA outcomes')
class CompletedTwoEAReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=report.load(ROOT/'RESULTS.json');cls.reference=report.load(ROOT.parent/'RESULTS.json')

    def test_all_four_cash_curves_daily_and_monthly_reconcile(self):
        plan=report.prior.normalized_plan(self.data)
        primary=report.reference_results(self.data)
        self.assertEqual(len(primary),4)
        self.assertEqual(set(plan['priority']),set(report.SLUGS))
        for r in primary:
            days,months=report.prior.base.cash_periods(r,plan)
            expected=r['metrics']['ending_balance']-plan.get('initial_balance',1000)
            self.assertAlmostEqual(sum(d['net_cash'] for d in days),expected,places=7)
            self.assertAlmostEqual(sum(m['net_cash'] for m in months),expected,places=7)
            self.assertEqual(sum(d['closes'] for d in days),len(r['trades']))
            self.assertEqual(sum(d['entries'] for d in days),report.prior.entries(r))
            self.assertTrue(all(d['ea'] in report.SLUGS for d in r['decisions']))

    def test_final_report_actual_links_and_matched_reference(self):
        html=report.render(self.data,self.reference,ROOT);p=Parse();p.feed(html)
        self.assertNotIn('@@',html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertEqual(len(p.paths),4)
        for link in p.hrefs:
            if not link.startswith(('https:','http:','#')):
                self.assertTrue((ROOT/link.replace('%20',' ')).is_file(),link)
        old=report.reference_results(self.reference)
        for r in report.reference_results(self.data):
            matched=[o for o in old if o['scenario']['id']==r['scenario']['id'] and o['stress']==r['stress']]
            self.assertEqual(len(matched),1)


if __name__=='__main__':unittest.main()

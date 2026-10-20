"""Presentation tests for separate delivery and common-policy comparisons."""
from copy import deepcopy
from datetime import datetime,timezone
from html.parser import HTMLParser
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('top5_prop_comparison_report_test',ROOT/'report.py')
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)


def fixture():
    def epoch(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
    start=epoch('2026-08-17');op=epoch('2026-09-01T12:00:00');end=epoch('2026-10-16T23:59:59')
    roster5=['gold-overnight-value-area','xau-rsi-vwap','nasdaq-overnight','nasdaq-5m-candle-momentum','orb-volume-profile']
    roster9=['xau-rsi-vwap','us100-h1-orb-13utc','nasdaq-5m-candle-momentum','usdjpy-london-open-momentum',
        'xau-orb-london-ny-overlap-m30','us100-month-end-flow','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30']
    plan=dict(window_utc=['2026-08-17T00:00:00+00:00','2026-10-17T00:00:00+00:00'],initial_balance=1000,
        portfolios=dict(top5=roster5,prop_ready=roster9))
    closed=dict(id='rsi|1',ea='xau-rsi-vwap',symbol='XAUUSD',side='buy',op=op,cl=op+300,
        lots=.1,risk=50,entry_cash=-1,exit_cash=11.1,net=10.1,gross=12,commission=-1.9,swap=0,balance=1010.1)
    first=dict(id='rsi|1',ea='xau-rsi-vwap',epoch=op,equity=1000,budget=50,reason='opened',
        stop_risk=50,volume=.1,minimum_lot_risk=5)
    second=dict(id='nq|1',ea='nasdaq-5m-candle-momentum',epoch=op+600,equity=1010.1,budget=50,
        reason='opened',stop_risk=49,volume=.27,minimum_lot_risk=9)
    r=dict(stress=False,metrics=dict(trades=1,win_rate_pct=100,profit_factor=None,
        profit_factor_status='no_losing_trades',ending_balance=1010,ending_sampled_equity=1012,
        return_pct=1,ending_equity_return_pct=1.2,open_positions=1,max_closed_dd_pct=.2,
        max_sampled_equity_dd_pct=2,max_daily_closed_dd_cash=2,max_daily_sampled_equity_dd_cash=20,
        max_win_streak=1,max_loss_streak=0,daily_closed_return_sharpe=1.1,hard_loss_latch=False,
        average_trades_per_calendar_day=1/61,average_trades_per_weekday=1/45),
        trades=[closed],decisions=[first,second],per_ea={'xau-rsi-vwap':dict(candidates=1,opened=1,closed=1),
            'nasdaq-5m-candle-momentum':dict(candidates=1,opened=1)},
        curve=[dict(epoch=start,balance=1000,equity=1000),dict(epoch=op,balance=999,equity=999),
            dict(epoch=op+300,balance=1010.1,equity=1010.1),dict(epoch=op+600,balance=1010,equity=1010),
            dict(epoch=end,balance=1010,equity=1012)],
        open_positions=[dict(ea='nasdaq-5m-candle-momentum',op=op+600,lots=.27,initial_risk=49,
            paid_entry_cash=-.1,mark_epoch=end-600,sampled_floating=2)],mark_quality={'owned_marks':3})
    results=[]
    for view in report.VIEWS:
        for stress in (False,True):
            for portfolio in report.PROFILES:
                for scenario in ('fixed50','compound5'):
                    item=deepcopy(r);item.update(portfolio=portfolio,view=view,stress=stress)
                    item['scenario']=dict(id=scenario,mode='fixed' if scenario=='fixed50' else 'percent',
                        label='Fixed $50' if scenario=='fixed50' else '5% current equity')
                    results.append(item)
    cov=dict(ea='xau-rsi-vwap',candidates=2,end_censored=1,owned_marks=3,first_epoch=start,last_epoch=end,
        native={'history_quality':'100% real ticks'})
    return dict(plan=plan,results=results,coverage={'top5':[cov],'prop_ready':[cov]})


class Parse(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[];self.paths=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='path':self.paths.append(a.get('d',''))


class ComparisonReportTests(unittest.TestCase):
    def test_no_empty_or_partial_result_claims(self):
        for size in (0,1,15):
            data=fixture();data['results']=data['results'][:size]
            with self.assertRaises(ValueError):report.render(data)

    def test_duplicate_cases_rejected(self):
        data=fixture();data['results'][-1]=deepcopy(data['results'][0])
        with self.assertRaises(ValueError):report.render(data)

    def test_sixteen_cases_four_panels_without_policy_mixing(self):
        html=report.render(fixture());p=Parse();p.feed(html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertEqual(len([s for s in p.ids if s.startswith('case-')]),16)
        self.assertEqual(len([s for s in p.ids if s.endswith(('-source','-stress')) and not s.startswith('chart-title-')]),4)
        self.assertEqual(len(p.paths),16)
        self.assertNotIn('@@',html)

    def test_as_packaged_risk_inequality_and_common_not_deployed(self):
        html=report.render(fixture())
        for phrase in ('not equal risk','percentage of current <strong>balance</strong>',
            '<strong>$5 reference cap</strong>','override can exceed selected risk',
            'strict down-round/skip','hypothetical and not installed',
            'not a clean isolated DI-only experiment','not exact historical Pro repricing'):
            self.assertTrue(phrase in html,phrase)

    def test_closed_cash_equity_open_entry_bridge(self):
        data=fixture();html=report.render(data)
        for phrase in ('$1,010.00','$1,012.00','+$10.10','−$0.10','+$2.00','unbanked floating',
            'Closed-position PF/win rate/streaks exclude open positions'):
            self.assertTrue(phrase in html,phrase)
        for r in data['results']:
            days,months=report.base.cash_periods(r,report.plan_for(data,r))
            self.assertAlmostEqual(sum(d['net_cash'] for d in days),10)
            self.assertAlmostEqual(sum(m['net_cash'] for m in months),10)

    def test_override_counts_only_admitted_and_real_risk(self):
        r=fixture()['results'][0]
        r['decisions'][0]['minimum_lot_override']=True
        skipped=deepcopy(r['decisions'][0]);skipped['reason']='margin_proxy'
        r['decisions'].append(skipped)
        admitted,risks,ratios,overrides=report.risk_observations(r)
        self.assertEqual(len(admitted),2);self.assertEqual(overrides,1)
        self.assertEqual(risks,[50,49]);self.assertEqual(ratios[0],5)

    def test_capital_exhaustion_never_called_executable(self):
        data=fixture();r=data['results'][0];r['metrics']['capital_exhaustion_epoch']=r['curve'][1]['epoch']
        self.assertTrue('later path not executable' in report.validity(r))
        html=report.render(data)
        for phrase in ('Sampled capital exhaustion occurred','cannot be promoted as an executable account path',
            'broker stopout','not a safety guarantee'):
            self.assertTrue(phrase in html,phrase)

    def test_all_chart_paths_are_inside_bounds(self):
        p=Parse();p.feed(report.render(fixture()))
        for path in p.paths:
            self.assertTrue('nan' not in path.lower() and 'inf' not in path.lower())
            for x,y in re.findall(r'[ML]([\d.]+),([\d.]+)',path):
                self.assertTrue(0<=float(x)<=1000);self.assertTrue(0<=float(y)<=220)

    def test_open_mark_timestamp_and_horizon_age(self):
        data=fixture();r=data['results'][0]
        html=report.open_positions(r,report.plan_for(data,r))
        self.assertTrue('2026-10-16 23:49:59' in html)
        self.assertTrue('600' in html)
        self.assertTrue('Paid entry cash' in html)

    def test_string_escaping(self):
        data=fixture();evil='<script>alert(1)</script>'
        data['results'][0]['scenario']['label']=evil
        self.assertNotIn(evil,report.render(data))
        self.assertTrue('&lt;script&gt;' in report.render(data))

    def test_only_existing_public_evidence_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'native').mkdir()
            for name in ('RESULTS.json','PLAN.json','native/native_cases.json'):
                (root/name).write_text('{}',encoding='utf-8')
            p=Parse();p.feed(report.evidence(root))
            self.assertEqual(set(p.links),{'RESULTS.json','PLAN.json','native/native_cases.json'})
            self.assertTrue(all((root/link).is_file() for link in p.links))

    def test_audit_must_match_the_exact_result_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);result=root/'RESULTS.json'
            result.write_text('{}',encoding='utf-8')
            receipt=dict(status='PASS',result_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),checks=1)
            (root/'VERIFICATION.json').write_text(json.dumps(receipt),encoding='utf-8')
            self.assertEqual(report.verified_receipt(root)['checks'],1)
            result.write_text('{"changed":true}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'exact results'):report.verified_receipt(root)
            result.write_text('{}',encoding='utf-8');receipt['status']='FAIL'
            (root/'VERIFICATION.json').write_text(json.dumps(receipt),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not PASS'):report.verified_receipt(root)


@unittest.skipUnless((ROOT/'RESULTS.json').is_file(),'Waiting for frozen sixteen-case comparison')
class CompletedComparisonReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=report.load(ROOT/'RESULTS.json')

    def test_all_sixteen_case_cash_calendars_reconcile(self):
        self.assertEqual(len(self.data['results']),16)
        for r in self.data['results']:
            with self.subTest(profile=report.profile(r),view=report.view(r),risk=r['scenario']['id'],stress=r['stress']):
                plan=report.plan_for(self.data,r)
                days,months=report.base.cash_periods(r,plan)
                expected=r['metrics']['ending_balance']-plan.get('initial_balance',1000)
                self.assertAlmostEqual(sum(d['net_cash'] for d in days),expected,places=7)
                self.assertAlmostEqual(sum(m['net_cash'] for m in months),expected,places=7)
                self.assertEqual(sum(d['closes'] for d in days),len(r['trades']))
                self.assertEqual(sum(d['entries'] for d in days),len(report.risk_observations(r)[0]))
                self.assertEqual(sum(v.get('closed',0) for v in r['per_ea'].values()),len(r['trades']))

    def test_actual_report_structure_links_and_rosters(self):
        html=report.render(self.data,ROOT);p=Parse();p.feed(html)
        self.assertEqual(len(p.paths),16)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertNotIn('@@',html)
        for link in p.links:
            if not link.startswith(('https:','http:','#')):self.assertTrue((ROOT/link.replace('%20',' ')).is_file(),link)
        self.assertEqual(len(self.data['plan']['portfolios']['top5']),5)
        self.assertEqual(len(self.data['plan']['portfolios']['prop_ready']),9)

    def test_real_outcome_warning_is_not_a_winner_or_prop_pass_claim(self):
        verification=report.verified_receipt(ROOT)
        html=report.findings(self.data['results'],verification)
        for phrase in ('5% risk is not supported as prop-safe','+3.82%','54.54%',
            '-4.93%','-6.70%','$131.00','$50.00','12.63%',
            '14 entries','17 in 5%-balance mode','All eight common-policy cases lost cash',
            'not an FTMO account model','No 60–70% pass-rate result is computed',
            'floating profit is not banked','not a trading edge'):
            self.assertTrue(phrase in html,phrase)

    def test_verified_weekend_gap_not_mislabelled_end_liquidation(self):
        verification=report.verified_receipt(ROOT);gap=verification['largest_gap_loss']
        self.assertEqual(verification['status'],'PASS')
        self.assertGreater(verification['checks'],800000)
        self.assertFalse(gap['end_censored'])
        self.assertAlmostEqual(gap['planned_stop_cash'],49.1568)
        self.assertAlmostEqual(gap['net'],-91.8)
        html=report.findings(self.data['results'],verification)
        for phrase in ('A real stop gap broke the research loss floor',
            '2026-09-11T13:35:00+00:00','2026-09-13T22:00:27+00:00',
            '29,425.00','29,249.44','29,118.45','130.99 points',
            '−$91.80','−$5.79','$778.69','genuine source stop fill',
            'not synthetic final liquidation or a sizing bug'):
            self.assertTrue(phrase in html,phrase)

    def test_top5_open_cash_and_equity_never_conflated(self):
        r=next(r for r in self.data['results'] if report.profile(r)=='top5' and
            report.view(r)=='as_packaged' and r['scenario']['id']=='fixed50' and not r['stress'])
        m=r['metrics'];closed_net=sum(t['net'] for t in r['trades'])
        self.assertEqual(m['open_positions'],2)
        self.assertAlmostEqual(m['ending_balance'],1038.17)
        self.assertAlmostEqual(m['ending_sampled_equity'],1202.7151851851856)
        self.assertAlmostEqual(m['ending_balance']-1000-closed_net,-.23,places=7)
        html=report.cash_bridge([r],1000)+report.open_positions(r,report.plan_for(self.data,r))
        for phrase in ('−$0.23','+$164.55','2026-10-16 20:50:00','11,399',
            'not banked or part of closed PF/win rate'):
            self.assertTrue(phrase in html,phrase)


if __name__=='__main__':unittest.main()

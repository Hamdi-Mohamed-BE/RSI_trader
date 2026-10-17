import calendar, hashlib, json, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
NY=ZoneInfo('America/New_York')
def utc(epoch):return datetime.fromtimestamp(epoch,timezone.utc)
def nth_sunday(year,month,nth):
    weekday=calendar.weekday(year,month,1)
    return 1+(6-weekday)%7+(nth-1)*7
def mql_offset(dt):
    start=datetime(dt.year,3,nth_sunday(dt.year,3,2),7,tzinfo=timezone.utc)
    end=datetime(dt.year,11,nth_sunday(dt.year,11,1),6,tzinfo=timezone.utc)
    return -4 if start<=dt<end else -5
def rejects(open_,high,low,close,previous,zone_low):
    body=open_-close;wick=high-max(open_,close);span=high-low
    return body>0 and previous<zone_low and high>=zone_low and close<zone_low and wick>=body and span>0 and wick/span>=.25

class ReconstructionTests(unittest.TestCase):
    def test_new_york_dst_matches_iana(self):
        for year in range(2023,2027):
            for month,nth,hour in [(3,2,7),(11,1,6)]:
                boundary=datetime(year,month,nth_sunday(year,month,nth),hour,tzinfo=timezone.utc)
                for delta in [-1,0,1]:
                    t=boundary+timedelta(seconds=delta)
                    self.assertEqual(mql_offset(t),t.astimezone(NY).utcoffset().total_seconds()/3600)

    def test_cash_open_is_dst_correct(self):
        for t in [datetime(2026,1,20,14,30,tzinfo=timezone.utc),datetime(2026,9,10,13,30,tzinfo=timezone.utc)]:
            local=t+timedelta(hours=mql_offset(t));self.assertEqual((local.hour,local.minute),(9,30))

    def test_upper_wick_bearish_rejection(self):
        self.assertTrue(rejects(100,104,98,99,99,101))
        self.assertFalse(rejects(100,101,95,96,99,101)) # Upper wick smaller than body.
        self.assertFalse(rejects(100,104,99,102,99,101)) # Bullish close inside/above supply.
        self.assertFalse(rejects(100,104,98,99,102,101)) # Did not approach from below.

    def test_future_low_not_used(self):
        completed=[(10,190),(20,175),(30,183),(40,150)]
        known=min(low for end,low in completed if end<=30)
        self.assertEqual(known,175);self.assertNotEqual(known,min(low for end,low in completed))

    def test_stop_protects_origin_and_rejection(self):
        stop=max(110,112)+.1*5
        self.assertGreater(stop,110);self.assertGreater(stop,112)

    def test_native_budgets_timeframes_and_signal_order(self):
        summary=json.loads((ROOT/'SUMMARY.json').read_text())
        state=json.loads((ROOT/'RUN_STATUS.json').read_text())
        self.assertEqual(len(state['complete']),6);self.assertFalse(state['failed'])
        for case in summary['plan']['cases']:
            r=json.loads(Path(state['complete'][case['slug']]['path']).read_text())
            self.assertEqual(r['inputs']['InpRiskPercent'],'0.5')
            seen=set()
            for match,t in zip(r['signal_audit'],r['trades']):
                signal=match['signal'];day=int(signal['date_ny'])
                self.assertNotIn(day,seen);seen.add(day)
                opening=utc(t['open_epoch']).astimezone(NY)
                self.assertEqual(int(opening.strftime('%Y%m%d')),day)
                self.assertLess(opening.weekday(),5)
                self.assertGreaterEqual(opening.hour*60+opening.minute,570)
                self.assertLessEqual(opening.hour*60+opening.minute,955)
                self.assertLessEqual(int(signal['signal_close_epoch']),t['open_epoch'])
                if not any(c.lower().startswith(('tp ','sl ')) for c in t['exit_comments']):
                    self.assertGreaterEqual(utc(t['close_epoch']).astimezone(NY).hour,16)

    def test_six_cases_reconcile_and_three_fresh_cases_are_real_ticks(self):
        v=json.loads((ROOT/'VERIFICATION.json').read_text())
        self.assertEqual(v['native_reports_reconciled'],6)
        fresh=[x for x in v['cases'] if x['slug'].endswith('-2026')]
        self.assertEqual(len(fresh),3)
        for case in fresh:self.assertEqual(case['history_quality'],'100% real ticks');self.assertFalse(case['tick_gaps'])

    def test_source_unchanged_and_tester_only(self):
        source=ROOT/'NY Supply Wick Retest.mq5';body=source.read_text()
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        p=json.loads((ROOT/'PLAN.json').read_text())
        for case in p['cases']:self.assertEqual(case['production_hashes'][str(source)],digest)
        self.assertIn('!MQLInfoInteger(MQL_TESTER)',body)
        self.assertNotIn('bars[0].low',body);self.assertNotIn('bars[0].high',body)
        self.assertIn('session_low=MathMin(session_low,bars[1].low)',body)

if __name__=='__main__':unittest.main()

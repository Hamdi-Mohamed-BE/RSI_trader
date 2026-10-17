"""Synthetic tests: no broker, MT5, website or portfolio writes."""
import unittest
import numpy as np
from run import one_path, resets, start_paths, source_array, load_inputs, FIELDS

def trade(op, duration=.01, rr=1., symbol=0, news=False, unit=100., quick=False):
    return [op, duration, unit, rr, news, symbol, symbol, 1., 0., 0., quick, symbol, 1.]

def replay(rows, *, policy=1, firm=0, mode=0, stage=-1, days=90, portfolio=1):
    a=np.asarray(rows,float).reshape(-1,13)
    out,log=one_path(a,np.array([0],np.int64),days,days,
        resets('2025-10-06',days,'Etc/UTC'),firm,portfolio,policy,mode,stage,25000.,False,True)
    return dict(zip(FIELDS,out)),log

class RiskResearchTests(unittest.TestCase):
    def test_video_arithmetic_not_same_as_standard_ten_percent(self):
        self.assertAlmostEqual(2000/7,285.7142857)
        self.assertAlmostEqual((2000+2*(2000/7))/7,367.3469388)
        self.assertAlmostEqual((50000*.10)/7/50000*100,1.42857142857)

    def test_literal_sizes_from_closed_buffer_not_future_profit(self):
        a,la=replay([trade(.1,.2,1),trade(.2,.2,2),trade(.5,.01,1)])
        b,lb=replay([trade(.1,.2,-1),trade(.2,.2,-2),trade(.5,.01,1)])
        self.assertEqual(la[0,3],357.)
        self.assertEqual(la[1,3],357.)
        self.assertEqual(lb[0,3],la[0,3])
        self.assertEqual(lb[1,3],la[1,3])
        self.assertGreater(la[2,3],357.)
        self.assertLess(lb[2,3],357.)

    def test_lots_round_down_and_skip_below_minimum(self):
        a,log=replay([trade(.1,unit=10000),trade(.2,unit=100000)])
        self.assertEqual(log[0,3],300.)
        self.assertEqual(a['trades'],1)
        self.assertEqual(a['skipped_entries'],1)

    def test_parallel_risk_literal_fails_reserve_guarded_does_not(self):
        rows=[trade(.1,.2,1,symbol=i) for i in range(6)]
        literal,_=replay(rows,mode=1,stage=2)
        guard,_=replay(rows,mode=1,stage=2,policy=2)
        self.assertEqual(literal['cause'],1)
        self.assertEqual(guard['cause'],0)
        self.assertGreater(guard['skipped_entries'],0)
        self.assertLessEqual(guard['max_open_risk_pct_initial'],2.000001)

    def test_repeated_losses_can_hit_daily_before_total_floor(self):
        rows=[trade(.1+i*.02,.01,-1) for i in range(10)]
        out,_=replay(rows,stage=2)
        self.assertEqual(out['cause'],1)
        self.assertGreater(out['final_balance'],22500)

    def test_unrestricted_history_does_not_freeze_at_target(self):
        rows=[trade(.1+i,.1,10) for i in range(12)]
        out,_=replay(rows,policy=0)
        self.assertEqual(out['trades'],12)
        self.assertGreater(out['closed_return_pct'],10)

    def test_challenge_requires_entry_days_and_flat(self):
        # A very large first profit is not a pass with fewer than four entry days.
        short,_=replay([trade(.1,.01,30)],stage=0,policy=0)
        self.assertEqual(short['phase1'],0)
        rows=[trade(.1+i,.01,6) for i in range(12)]
        out,_=replay(rows,stage=0,policy=0)
        self.assertEqual(out['funded'],1)
        self.assertGreaterEqual(out['pass_days'],9)

    def test_fundednext_news_credit_wins_only(self):
        out,log=replay([trade(.1,.01,1,news=True),trade(.2,.01,-1,news=True)],firm=1,stage=2,policy=0)
        self.assertAlmostEqual(log[0,1],50.)
        self.assertAlmostEqual(log[1,1],-125.)

    def test_fundednext_quick_strike_gate(self):
        rows=[trade(.1+i,20/86400,10,quick=True) for i in range(12)]
        challenge,_=replay(rows,firm=1,stage=0,policy=0)
        funded,_=replay(rows,firm=1,stage=2,policy=0)
        self.assertEqual(challenge['phase1'],0)
        self.assertEqual(funded['cause'],4)

    def test_inactivity_only_applies_to_actual_account_trials(self):
        rows=[trade(.1,.01,1),trade(70,.01,1)]
        hist,_=replay(rows,firm=2,stage=-1)
        funded,_=replay(rows,firm=2,stage=2)
        self.assertEqual(hist['trades'],2)
        self.assertEqual(hist['cause'],0)
        self.assertEqual(funded['cause'],3)

    def test_weekday_blocks_retain_duration_and_coincident_orders(self):
        starts,block=start_paths(365,180,'bootstrap',25,42)
        self.assertEqual(block,28)
        self.assertTrue(np.all(starts%7==0))
        rows=[trade(.1,.5,1),trade(.1,.5,1,symbol=1)]
        out,log=replay(rows)
        self.assertAlmostEqual(log[0,0],.6)
        self.assertAlmostEqual(log[1,0],.6)
        self.assertEqual(out['max_open_risk_pct_initial'],714/25000*100)

    def test_dst_reset_and_evidence_membership(self):
        r=resets('2026-03-28',5,'Europe/Prague')
        self.assertTrue(np.any(np.isclose(np.diff(r),23/24)))
        _,ledger,meta=load_inputs()
        self.assertEqual(len(meta['orbs-only']['members']),5)
        self.assertTrue(all(m['target_rr']==.5 for m in meta['orbs-only']['members']))
        a,k,s,c=source_array(ledger['full-eas'],'2025-10-06','2026-10-06')
        self.assertEqual(c['covered_members'],36)
        self.assertNotIn('gold-news-v9-direction',k)

if __name__=='__main__':unittest.main(verbosity=2)

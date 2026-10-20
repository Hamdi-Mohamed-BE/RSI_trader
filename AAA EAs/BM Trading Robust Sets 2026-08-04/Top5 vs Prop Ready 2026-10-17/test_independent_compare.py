"""Synthetic checks of the independent packaged-client auditor itself."""
import copy
import unittest
import independent_verify as v
import test_compare as t

r=t.r
PLAN=dict(window_utc=[r.base.iso(r.base.START),r.base.iso(r.base.END)],initial_balance=1000.,
          portfolios=dict(top5=list(r.TOP5)))


def replay(rows,stress=False):
    b=t.broker()
    if stress:b['symbols']['USTEC']['quote_spread']=2.
    for q in rows:
        q['receipt_margin_one_lot']=b['symbols'][q['symbol']]['buy_margin_one_lot']
    model=r.ClientReplay(t.scenario(),b,stress)
    data=dict(candidates=rows)
    events=r.base.events_for(dict(priority=list(r.TOP5)),data)
    for stamp,kind,_,_,q,mark in events:
        if not r.base.START<=stamp<r.base.END:continue
        if kind==0:model.observe(stamp)
        elif kind in (1,4):model.closing(q,stamp)
        elif kind==2:model.mark(q,mark,stamp)
        else:model.opening(q,stamp)
    return model.result(),data,b


class IndependentClientAuditor(unittest.TestCase):
    def check_case(self,q,stress=False):
        q['ea']=r.TOP5[0]
        result,data,b=replay([q],stress)
        summary,_=v.client_audit(result,data,PLAN,b)
        self.assertEqual(summary['ending_cash'],result['metrics']['ending_balance'])
        return result,data,b

    def test_normal_fee_and_swap_case(self):
        self.check_case(t.row(gross=100.,commission=-10.,swap=-4.,entry_cost=-3.))

    def test_spread_stress_case(self):
        self.check_case(t.row(gross=100.,commission=-10.,swap=-4.,entry_cost=-3.),True)

    def test_censored_fees_and_open_marks(self):
        q=t.row(duration=None,entry_cost=-3.)
        q['marks']=[[q['op']+1,20.,None]]
        self.check_case(q)

    def test_minimum_lot_override(self):
        self.check_case(t.row(unit=2000.))

    def test_exhausted_cash_calendar(self):
        self.check_case(t.row(gross=-2000.))

    def test_negative_cash_calendar(self):
        self.check_case(t.row(gross=-2200.))

    def test_mutated_admission_is_detected(self):
        result,data,b=self.check_case(t.row())
        bad=copy.deepcopy(result)
        bad['decisions'][0]['volume']+=.01
        with self.assertRaises(AssertionError):v.client_audit(bad,data,PLAN,b)


if __name__=='__main__':unittest.main(verbosity=2)

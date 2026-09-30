import unittest
from simulate import replay, target_risk, sized_volume

CONTRACT=dict(volume_min=.01,volume_step=.01,volume_max=200,trade_contract_size=100)

def rows(outcomes):
    return [dict(number=i+1,open_time=f'2026-01-{i+1:02d}T12:00:00+00:00',
                 close_time=f'2026-01-{i+1:02d}T13:00:00+00:00',side='Long',
                 volume=1,initial_risk_usd=100,gross_profit=r*100,commission=0,swap=0,net_profit=r*100)
            for i,r in enumerate(outcomes)]

class RiskTests(unittest.TestCase):
    def test_geometric_and_reset(self):
        s,r=replay(rows([-1,-1,.5,-1]),'loss_1_5x',CONTRACT,rounding=False)
        self.assertEqual([x['requested_risk'] for x in r],[50,75,112.5,50])
        self.assertAlmostEqual(s['net_profit'],-118.75)
    def test_fixed_alternative(self):
        _,r=replay(rows([-1,-1,.5,-1]),'fixed_75_after_loss',CONTRACT,rounding=False)
        self.assertEqual([x['requested_risk'] for x in r],[50,75,75,50])
    def test_zero_does_not_reset(self):
        _,r=replay(rows([-1,0,1]),'loss_1_5x',CONTRACT,rounding=False)
        self.assertEqual([x['requested_risk'] for x in r],[50,75,75])
    def test_round_up_minimum(self):
        self.assertEqual(sized_volume(50,10000,True,CONTRACT),.01)
        self.assertAlmostEqual(sized_volume(50,900,True,CONTRACT),.06)
    def test_flat_ideal(self):
        s,_=replay(rows([1,-1,.5]),'flat',CONTRACT,rounding=False)
        self.assertAlmostEqual(s['net_profit'],25)
        self.assertEqual(s['trades'],3)
    def test_costs_change_state(self):
        rr=rows([.001,1]); rr[0].update(commission=-1,net_profit=-.9)
        _,r=replay(rr,'loss_1_5x',CONTRACT,rounding=False)
        self.assertEqual(r[1]['requested_risk'],75)
    def test_prefix_no_lookahead(self):
        _,a=replay(rows([-1,1,-1,1]),'loss_1_5x',CONTRACT,rounding=False)
        _,b=replay(rows([-1,1,-1,-1]),'loss_1_5x',CONTRACT,rounding=False)
        self.assertEqual([r['volume'] for r in a],[r['volume'] for r in b])
    def test_overlap_rejected(self):
        rr=rows([1,1]); rr[0]['close_time']='2026-01-03T13:00:00+00:00'
        with self.assertRaises(ValueError):replay(rr,'flat',CONTRACT)
    def test_no_unrequested_cap(self):
        self.assertAlmostEqual(target_risk('loss_1_5x',5),379.6875)

if __name__=='__main__':unittest.main()

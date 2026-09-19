import unittest
from verify import direction,pivot,reject

class RulesTest(unittest.TestCase):
    def candles(self,first=(10,5),last=(12,7)):
        return [dict(high=first[0],low=first[1]) for _ in range(7)]+[dict(high=last[0],low=last[1]) for _ in range(7)]
    def test_daily_higher_range(self):self.assertEqual(direction(self.candles()),1)
    def test_daily_lower_range(self):self.assertEqual(direction(self.candles(last=(8,3))),-1)
    def test_expanding_not_directional(self):self.assertEqual(direction(self.candles(last=(12,3))),0)
    def test_inside_not_directional(self):self.assertEqual(direction(self.candles(last=(9,6))),0)
    def test_equal_extremes_not_directional(self):self.assertEqual(direction(self.candles(last=(10,5))),0)
    def test_high_requires_both_right_bars(self):
        b=[dict(high=v,low=0) for v in [1,2,5,3,4]]
        self.assertFalse(pivot(b[:4],2,True));self.assertTrue(pivot(b,2,True))
    def test_equal_swing_is_not_strict(self):
        self.assertFalse(pivot([dict(high=v,low=0) for v in [1,2,5,3,5]],2,True))
    def test_low_requires_both_right_bars(self):
        b=[dict(low=v,high=10) for v in [5,4,1,3,2]]
        self.assertFalse(pivot(b[:4],2,False));self.assertTrue(pivot(b,2,False))
    def test_buy_wick_body_must_clear_zone(self):
        b=dict(open=12,close=13,low=10.5,high=14)
        self.assertTrue(reject(b,1,10,11));b['close']=11
        self.assertFalse(reject(b,1,10,11));b['close']=13;b['low']=9.9
        self.assertFalse(reject(b,1,10,11))
    def test_sell_wick_is_mirror(self):
        b=dict(open=8,close=9,low=7,high=10.5)
        self.assertTrue(reject(b,-1,10,11));b['close']=10
        self.assertFalse(reject(b,-1,10,11))
if __name__=='__main__':unittest.main()

import unittest

def fvg(first,third):
    if third['low']>first['high']:return 1,first['high'],third['low'],first['low']
    if third['high']<first['low']:return -1,third['high'],first['low'],first['high']
    return 0,0,0,0
def touch(direction,low,high,price):
    if direction==1 and price<low:return 'invalidate'
    if direction==-1 and price>high:return 'invalidate'
    return 'enter' if low<=price<=high else 'wait'

class Rules(unittest.TestCase):
    def test_bull(self):self.assertEqual(fvg({'high':100,'low':90},{'high':110,'low':101}),(1,100,101,90))
    def test_bear(self):self.assertEqual(fvg({'high':110,'low':100},{'high':99,'low':90}),(-1,99,100,110))
    def test_equal_is_not_gap(self):self.assertEqual(fvg({'high':100,'low':90},{'high':110,'low':100})[0],0)
    def test_overlap_is_not_gap(self):self.assertEqual(fvg({'high':100,'low':90},{'high':105,'low':95})[0],0)
    def test_bull_touch(self):self.assertEqual(touch(1,100,101,100.5),'enter')
    def test_bull_invalidation(self):self.assertEqual(touch(1,100,101,99.9),'invalidate')
    def test_bear_touch(self):self.assertEqual(touch(-1,99,100,99.5),'enter')
    def test_bear_invalidation(self):self.assertEqual(touch(-1,99,100,100.1),'invalidate')
    def test_two_r(self):
        entry,stop=101,90
        self.assertEqual(entry+2*(entry-stop),123)
    def test_mirrored_two_r(self):
        entry,stop=99,110
        self.assertEqual(entry-2*(stop-entry),77)
if __name__=='__main__':unittest.main(verbosity=2)

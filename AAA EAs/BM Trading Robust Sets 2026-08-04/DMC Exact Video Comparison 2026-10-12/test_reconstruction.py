"""Independent arithmetic/chronology checks for a raw research report."""
import unittest
import make_report

def pivots(bodies,strength=2):
    out=[]
    for i in range(strength,len(bodies)-strength):
        left=bodies[i-strength:i];right=bodies[i+1:i+strength+1]
        if all(bodies[i]>x for x in left+right):out.append((i,i+strength,'high'))
        if all(bodies[i]<x for x in left+right):out.append((i,i+strength,'low'))
    return out

class ReconstructionChecks(unittest.TestCase):
    def test_pivot_cannot_be_known_before_confirmation(self):
        self.assertEqual(pivots([1,2,6,4]),[])
        self.assertEqual(pivots([1,2,6,4,3]),[(2,4,'high')])
    def test_future_extension_does_not_revise_confirmed_pivots(self):
        seed=[1,2,6,4,3,2,1,2,3]
        prefix=pivots(seed)
        extended=[x for x in pivots(seed+[7,8,3,2,1]) if x[1]<len(seed)]
        self.assertEqual(prefix,extended)
    def test_flat_breaks_streak(self):
        self.assertEqual(make_report.streaks([1,1,0,1,-1,-1,1]),(2,2))
    def test_tiny_sample_win_rate_uncertainty(self):
        low,high=make_report.wilson(2,2)
        self.assertLess(low,35);self.assertEqual(high,100)
    def test_no_sample_ci_is_unavailable(self):
        self.assertEqual(make_report.wilson(0,0),[None,None])

if __name__=='__main__':unittest.main()

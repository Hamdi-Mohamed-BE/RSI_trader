"""V3 exporter phase fixtures; no account, native results or replay outcomes."""
import unittest
import independent_verify as v


def trade(op=100,cl=1000,volume=.5,key=1):
    return dict(open_epoch=op,close_epoch=cl,volume=volume,position_id=key)


def point(t,balance=1000.,equity=1010.,phase='market_sample'):
    return dict(epoch=str(t),balance=str(balance),equity=str(equity),phase=phase)


class ExportPhaseCausality(unittest.TestCase):
    def test_post_liquidation_cash_never_becomes_owned_floating(self):
        trace=[point(200),point(250,balance=1040.,equity=1040.,phase='finish_after_native_liquidation')]
        marks,dropped=v.reconstructed_owned_marks([trade()],trace,0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])
        self.assertEqual(dropped['post_liquidation_snapshot'],1)

    def test_post_test_row_is_dropped_before_duplicate_market_timestamp(self):
        trace=[point(200,balance=1040.,equity=1040.,phase='finish_after_native_liquidation'),point(200)]
        marks,dropped=v.reconstructed_owned_marks([trade()],trace,0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])
        self.assertNotIn('duplicate_market_sample',dropped)

    def test_legacy_export_without_phase_remains_compatible(self):
        p=point(200)
        del p['phase']
        marks,_=v.reconstructed_owned_marks([trade()],[p],0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])

    def test_empty_legacy_phase_remains_compatible(self):
        marks,_=v.reconstructed_owned_marks([trade()],[point(200,phase='')],0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])

    def test_unknown_phase_fails_closed(self):
        with self.assertRaises(AssertionError):
            v.reconstructed_owned_marks([trade()],[point(200,phase='future_snapshot')],0,2000)

    def test_future_window_row_is_not_used(self):
        marks,_=v.reconstructed_owned_marks([trade()],[point(200),point(300)],0,300)
        self.assertEqual(marks[1],[(200,20.,None)])

    def test_exact_position_boundaries_are_not_floating_marks(self):
        marks,dropped=v.reconstructed_owned_marks([trade()],[point(100),point(200),point(1000)],0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])
        self.assertEqual(dropped['position_boundary'],2)

    def test_duplicate_market_samples_are_not_double_counted(self):
        marks,dropped=v.reconstructed_owned_marks([trade()],[point(200),point(200)],0,2000)
        self.assertEqual(marks[1],[(200,20.,None)])
        self.assertEqual(dropped['duplicate_market_sample'],1)

    def test_unowned_market_floating_fails_instead_of_attaching_elsewhere(self):
        with self.assertRaises(AssertionError):
            v.reconstructed_owned_marks([trade()],[point(1100)],0,2000)

    def test_unowned_finish_snapshot_is_discarded_without_fake_position(self):
        marks,dropped=v.reconstructed_owned_marks([trade()],[point(1100,phase='finish_after_native_liquidation')],0,2000)
        self.assertEqual(dict(marks),{})
        self.assertEqual(dropped['post_liquidation_snapshot'],1)

    def test_explicit_open_swap_is_per_lot_and_missing_remains_unknown(self):
        p=point(200)
        p['open_swap']='-2.50'
        marks,_=v.reconstructed_owned_marks([trade()],[p],0,2000)
        self.assertEqual(marks[1],[(200,20.,-5.)])


if __name__=='__main__':unittest.main(verbosity=2)

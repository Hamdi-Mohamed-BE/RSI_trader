import unittest
import numpy as np
import pandas as pd
from benchmark import score, stats


class CostTests(unittest.TestCase):
    def test_long_pays_entry_short_pays_exit(self):
        f = pd.DataFrame({'entry': [100., 100.], 'exit': [102., 98.],
                          'entry_spread': [.2, .3], 'exit_spread': [.4, .5]})
        r = score(f, np.array([1., -1.]))
        np.testing.assert_allclose(r.net, [1.53, 1.23])

    def test_drawdown_includes_initial_loss(self):
        r = stats(pd.DataFrame({'net': [-2., 5., -4., 1.]}))
        self.assertEqual(r['realized_dd_usd_per_oz'], 4.)
        self.assertEqual(r['pf'], 1.)


if __name__ == '__main__':
    unittest.main()

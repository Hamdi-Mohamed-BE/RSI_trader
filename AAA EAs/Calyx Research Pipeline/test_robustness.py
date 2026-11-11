from robustness import day_block_bootstrap, dependence, longest_losing_streak, max_drawdown


def t(day, v):
    return dict(close_time=f'2026-01-{day:02d}T10:00:00', net_profit=v, estimated_r=v)


def test_dependence_flags_best_day_sign_flip():
    rows = [t(1, -1), t(2, -1), t(3, 5), t(3, 1), t(4, -1)]
    dep = dependence(rows)
    assert dep['total'] == 3 and dep['best_day'] == {'date': '2026-01-03', 'value': 6}
    assert dep['without_best_day'] == -3 and dep['best_day_sign_flip'] is True
    assert dep['without_best_trade'] == -2 and dep['verdict'] == 'FAIL'


def test_dependence_passes_spread_out_profit():
    rows = [t(d, 1) for d in range(1, 11)] + [t(11, -1)]
    dep = dependence(rows)
    assert dep['verdict'] == 'PASS' and dep['without_best_day'] == 8 and dep['without_worst_day'] == 10


def test_dependence_not_applicable_for_losers():
    assert dependence([t(1, -1), t(2, 0.5)])['verdict'] == 'NOT_APPLICABLE_NON_POSITIVE_TOTAL'
    assert dependence([])['verdict'] == 'NO_TRADES'


def test_drawdown_and_streak():
    assert max_drawdown([1, -1, -2, 3, -1]) == 3
    assert longest_losing_streak([-1, -1, 0, -1, 1, -1, -1, -1]) == 3


def test_bootstrap_is_deterministic_and_ordered():
    rows = [t(d, (-1 if d % 3 else 2)) for d in range(1, 29)]
    a = day_block_bootstrap(rows, 21, paths=500, seed=7)
    b = day_block_bootstrap(rows, 21, paths=500, seed=7)
    assert a == b and a['source_days'] == 28
    assert a['max_drawdown']['p50'] <= a['max_drawdown']['p95'] <= a['max_drawdown']['p99']
    assert a['losing_streak']['p95'] >= a['losing_streak']['p50']


def test_three_monte_carlo_reshuffle_keeps_total_and_ranks_clumped_losses():
    from robustness import three_monte_carlo
    vals = [1.0] * 30 + [-1.0] * 15 + [1.0] * 30          # all losses in one clump: the worst possible order
    mc = three_monte_carlo(vals, runs=300, seed=3)
    assert mc['real'] == {'total': 45.0, 'max_drawdown': 15.0, 'losing_streak': 15}
    assert mc['reshuffle']['real_drawdown_worse_than_pct'] > 95 and mc['reshuffle']['max_drawdown']['p99'] <= 15
    assert mc['resample']['red_pct'] == 0.0
    assert three_monte_carlo(vals, runs=300, seed=3) == mc


def test_three_monte_carlo_randomize_separates_drop_and_cost():
    from robustness import three_monte_carlo
    vals = [0.1] * 200                                     # thin edge: +0.1 per trade
    mc = three_monte_carlo(vals, runs=200, seed=5, drop_fraction=0.1, extra_cost=0.2)
    r = mc['randomize']
    assert r['drop_only']['red_pct'] == 0.0                # dropping trades cannot turn an all-winner red
    assert r['cost_only']['red_pct'] == 100.0 and r['both']['red_pct'] == 100.0   # mean cost 0.2 > edge 0.1
    h = three_monte_carlo(vals, runs=50, seed=5, horizon=20)
    assert h['horizon_trades'] == 20 and h['reshuffle'] is None


# ---- 2026-11-11: cost stress, random-entry control, walk-forward with blind runs ----
import random as _random
from robustness import cost_stress, random_entry_control, rolling_folds, walk_forward


def test_cost_stress_multiplies_recorded_costs():
    res = cost_stress([1.0, -1.0, 0.5], [0.1, 0.1, 0.2])
    assert res['multiples']['1x']['total'] == 0.5
    assert res['multiples']['2x']['total'] == 0.1 and res['verdict'] == 'PASS'
    assert abs(res['multiples']['3x']['total'] + 0.3) < 1e-9
    assert abs(res['breakeven_multiple'] - 2.25) < 1e-9
    assert cost_stress([0.1, 0.1], [0.2, 0.2])['verdict'] == 'FAIL'


def _bars(days=120, drift=0.0, seed=1):
    rng = _random.Random(seed); out = []; p = 100.0; t0 = 1_700_000_000 - 1_700_000_000 % 86400
    for d in range(days):
        for m in range(0, 24 * 60, 15):
            o = p; p = p + drift + rng.gauss(0, 0.2); hi = max(o, p) + 0.05; lo = min(o, p) - 0.05
            out.append((t0 + d * 86400 + m * 60, o, hi, lo, p))
    return out


def test_random_entry_control_flags_lucky_and_skilled_trades():
    bars = _bars()
    skilled = [dict(open_epoch=bars[0][0] + 36000 + d * 86400, side=1, stop=1.0, target=1.0, hold_seconds=7200, r=1.0) for d in range(40)]
    res = random_entry_control(skilled, bars, copies=100)
    assert res['verdict'] == 'PASS' and res['p_value'] <= 0.02 and res['real_mean_r'] == 1.0
    unskilled = [dict(t, r=-0.2) for t in skilled]
    assert random_entry_control(unskilled, bars, copies=100)['verdict'] == 'FAIL'
    again = random_entry_control(skilled, bars, copies=100)
    assert again['random_mean_r'] == res['random_mean_r']          # deterministic for a seed


def test_walk_forward_finds_the_real_setting_and_beats_blind_runs():
    rng = _random.Random(7); day = 86400; start = 0; end = 6 * 365 * day
    ledgers = {}
    for k in range(10):
        edge = 0.25 if k in (6, 7) else -0.05                         # settings 6 and 7 (neighbours) hold a real edge
        ledgers[k] = [(e, edge + rng.gauss(0, 1)) for e in range(start, end, 2 * day)]
    neighbours = {k: [x for x in (k - 1, k + 1) if 0 <= x < 10] for k in range(10)}
    folds = rolling_folds(start, end, 1095, 365)
    assert len(folds) == 3 and folds[0][1] == folds[0][2]
    res = walk_forward(ledgers, neighbours, folds, min_trades=30, blind_runs=300)
    assert all(f['choice'] in (6, 7) for f in res['folds'])
    assert res['verdict'] == 'PASS' and res['blind']['p_value'] <= 0.05 and res['chained']['total'] > 0
    noise = {k: [(e, rng.gauss(-0.02, 1)) for e in range(start, end, 2 * day)] for k in range(10)}
    assert walk_forward(noise, neighbours, folds, min_trades=30, blind_runs=300)['verdict'] == 'FAIL'

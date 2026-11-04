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

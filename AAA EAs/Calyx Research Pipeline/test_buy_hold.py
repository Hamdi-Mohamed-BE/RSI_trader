from buy_hold import compare


def row(ret, dd):
    return dict(return_pct=ret, max_dd_pct=dd)


def test_beats_on_both():
    c = compare(row(50, 10), row(30, 20))
    assert c['verdict'] == 'BEATS on return and return/DD' and c['excess_return_pct'] == 20 and c['strategy_return_dd'] == 5.0 and c['hold_return_dd'] == 1.5


def test_higher_return_with_much_bigger_drawdown_is_not_a_clean_win():
    assert compare(row(60, 50), row(40, 20))['verdict'] == 'BEATS on return only, at a worse return/DD'


def test_lower_return_but_far_less_risk():
    assert compare(row(20, 5), row(40, 30))['verdict'] == 'LAGS on return, better return/DD'


def test_lags_on_both():
    assert compare(row(10, 20), row(40, 20))['verdict'] == 'LAGS on return and return/DD'

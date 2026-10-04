"""Additional, unchanged-profile recent evidence; preserves the full research index."""
from run_native import R, DEST, SOURCE, one, save, sha

if __name__ == '__main__':
    assert sha(DEST/'CalyxHourlyProfiles.ex5') == sha(SOURCE.with_suffix('.ex5'))
    rows = []
    for asset in ('US30', 'US100'):
        rows.append(one(asset, '6m'))
        save(R/'WEBSITE-NATIVE.json', rows)

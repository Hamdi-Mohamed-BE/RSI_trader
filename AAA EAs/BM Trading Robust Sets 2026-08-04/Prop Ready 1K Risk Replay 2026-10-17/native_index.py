"""Read-only source discovery, publishing no trading or portfolio outcomes."""
from pathlib import Path
import hashlib, json

R = Path(__file__).resolve().parent


def main():
    state = json.loads((R / 'native_status.json').read_text(encoding='utf-8'))
    plan = json.loads((R / 'native_plan.json').read_text(encoding='utf-8'))
    rows = []
    for case in plan['cases']:
        receipt = state['complete'].get(case['slug'])
        if receipt is None:
            continue
        path = Path(receipt['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
        rows.append(dict(slug=case['slug'], symbol=case['symbol'], path=str(path), **{
            k: v for k, v in receipt.items() if k != 'path'}))
    value = dict(start=plan['start'], end_exclusive=plan['end_exclusive'], cases=rows,
        complete=len(rows), total=9, native_source_only=True, no_live_changes=True,
        entry_risk_receipts='Each source folder/entry_risk.csv: position_id,deal,epoch,symbol,side,entry_price,sl,sl_source,unit_risk,calculation_ok,quote_bid,quote_ask,quote_epoch,source_volume,open_swap,margin_one_lot,margin_ok. OrderCalcProfit at native deal-add callback; not a pre-request quote.')
    (R / 'native_cases.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print('Published source index: ' + str(len(rows)) + '/9')


if __name__ == '__main__':
    main()

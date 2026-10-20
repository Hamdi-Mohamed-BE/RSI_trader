"""Independent read-only native source/provenance verification, no MT5 API."""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
from bisect import bisect_left
import csv
import gzip
import hashlib
import json
import math
import re


ROOT = Path(__file__).resolve().parent
CHECKS = Counter()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message, category):
    CHECKS[category] += 1
    if not ok:
        raise AssertionError(message)


def close(a, b, message, category, tolerance=1e-7):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance*max(1., abs(a), abs(b)),
            (message, a, b), category)


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(file))


def nonblank_lines(text):
    # Old Windows helper decodes CRLF without translation before write_text,
    # which may serialize an extra blank-only line. Keep every code/comment
    # line exactly; disregard only blank-only lines and line-ending encoding.
    return '\n'.join(line for line in text.splitlines() if line.strip())


def main():
    index, plan = load(ROOT/'native_cases.json'), load(ROOT/'native_plan.json')
    expected = {'gold-overnight-value-area', 'xau-rsi-vwap', 'nasdaq-overnight',
                'nasdaq-5m-candle-momentum', 'orb-volume-profile'}
    require(index['complete'] == index['total'] == 5, 'Five complete cases required', 'protocol')
    require({p['slug'] for p in index['cases']} == expected, 'Source roster differs', 'protocol')
    require(plan['fixed_source_risk_usd'] == 50 and plan['source_deposit'] == 10000 and
            plan['source_server'] == 'Exness-MT5Trial16' and plan['execution_delay_ms'] == 150 and
            plan['model'] == 4, 'Source protocol differs', 'protocol')
    for path in (ROOT/'FROZEN.json', ROOT/'RESUME FREEZE.json', ROOT/'EXPORT V3 FREEZE.json', ROOT/'CONTINUATION FREEZE.json'):
        frozen = load(path)
        for file, expected_hash in {**frozen['files'], **frozen.get('source_files', {})}.items():
            require(sha(file) == expected_hash, ('Frozen provenance changed', file), 'hashes')
    require(load(ROOT/'native_status.json')['failed']['gold-overnight-value-area']['error'] ==
            'Tester port occupied; no process stopped', 'Initial harmless failed postcondition not preserved', 'recovery')
    require(load(ROOT/'RESUME FREEZE.json')['original_native_protocol_unchanged'],
            'Recovery changed trading protocol', 'recovery')
    original_header = (ROOT/'ReadOnlyAuditBase.mqh').read_text(encoding='utf-8-sig')
    revised_header = (ROOT/'ReadOnlyAuditBaseV3.mqh').read_text(encoding='utf-8-sig')
    reversal = {
        'FileWrite(rr05_equity_file,"epoch","balance","equity","phase");':
        'FileWrite(rr05_equity_file,"epoch","balance","equity");',
        'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"market_sample");':
        'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));',
        'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"finish_after_native_liquidation");':
        'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));',
        '!HistorySelect(0,TimeCurrent()+86400)': '!HistorySelect(0,TimeCurrent())',
    }
    for before, after in reversal.items():
        require(revised_header.count(before) == 1, 'Extra/missing observational V3 edit', 'recovery')
        revised_header = revised_header.replace(before, after)
    require(nonblank_lines(revised_header) == nonblank_lines(original_header),
            'Non-observational V3 header differences', 'recovery')
    begin, end = (int(datetime.fromisoformat(x).replace(tzinfo=timezone.utc).timestamp())
                  for x in (plan['start'], plan['end_exclusive']))
    summaries = []
    for receipt in index['cases']:
        slug = receipt['slug']
        path = Path(receipt['path'])
        folder = path.parent
        case = load(path)
        row = next(p for p in plan['cases'] if p['slug'] == slug)
        require(sha(path) == receipt['sha256'], ('Result receipt SHA', slug), 'hashes')
        require(case['public_ex5_sha256'] == row['public_ex5_sha256'] == sha(row['public_expert']),
                ('Public client EX5 changed', slug), 'package')
        for key, value in row['inputs'].items():
            require(str(case['inputs'][key]).lower() == str(value).lower(), ('Actual input receipt', slug, key), 'package')
        require(case['inputs']['ClientRiskMode'] == '0' and case['inputs']['ClientRiskValue'] == '50',
                ('Actual source cash allocation', slug), 'package')
        if slug == 'nasdaq-5m-candle-momentum':
            require(case['inputs']['InpRequireDIAgreement'] == 'false', 'Nasdaq DI not OFF', 'package')
        build_path = Path(case.get('build_receipt_path', str(ROOT/'builds'/slug/'build.json')))
        build = load(build_path)
        require(build['callback_only_copy_verified'] and build['strategy_and_ClientGuard_graph_unchanged']
                and build['tester_only'] and build['compile'] == '0 errors, 0 warnings', 'Observational build provenance', 'package')
        require(build['binary_sha256'] == case['binary_sha256'] == sha(build_path.parent/'Audit.ex5'),
                'Fresh compiled audit EX5 hash', 'hashes')
        require(sha(build_path) == case['build_receipt_sha256'], 'Build receipt digest', 'hashes')
        require(sha(build_path.parent/'PublicWrapperCopy.mq5') == build['source_copy_sha256'] and
                sha(build_path.parent/'Audit.mq5') == build['audit_wrapper_sha256'], 'Compiled wrapper source hashes', 'package')
        source_wrapper = Path(row['wrapper'])
        expected_copy = source_wrapper.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        for callback, typename in (('OnInit', 'int'), ('OnTick', 'void'), ('OnTimer', 'void')):
            expression = r'\b'+typename+r'\s+'+callback+r'\s*\('
            require(len(re.findall(expression, expected_copy)) == 1, 'Public callback shape changed', 'package')
            expected_copy = re.sub(expression, typename+' Top5Package'+callback+'(', expected_copy)
        expected_copy = re.sub(r'(^\s*#include\s+)"([^\"]+)"',
            lambda match: match[1]+'"'+str((source_wrapper.parent/match[2].replace('\\', '/')).resolve()).replace('\\', '/')+'"',
            expected_copy, flags=re.M)
        require(nonblank_lines(expected_copy) == nonblank_lines((build_path.parent/'PublicWrapperCopy.mq5').read_text(encoding='utf-8-sig')),
                'Audited source is not callback-only copy of public package', 'package')
        journal = gzip.decompress((folder/'journal.private.txt.gz').read_bytes()).decode('utf-8')
        actual_servers = set(re.findall(r'authorized on (\S+) through', journal))
        require(actual_servers == {'Exness-MT5Trial16'}, 'Actual source authorization differs', 'feed')
        require('RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal,
                'Tester completion provenance', 'feed')
        require(not any(case['flags'][key] for key in ('initialization', 'runtime', 'history', 'stopout', 'export')),
                'Fatal source execution or coverage error flag present', 'feed')
        deals, risks = csv_rows(folder/'deals.csv'), csv_rows(folder/'entry_risk.csv')
        grouped = defaultdict(list)
        tickets = set()
        cash_net = 0.
        for d in deals:
            ticket = int(d['deal'])
            require(ticket not in tickets, 'Duplicate native deal', 'cash')
            tickets.add(ticket)
            grouped[int(d['position_id'])].append(d)
            cash_net += sum(float(d[k]) for k in ('gross', 'commission', 'swap', 'fee'))
        close(cash_net, case['native']['net_profit'], 'Native reported net', 'cash', .00001)
        close(cash_net, sum(p['net'] for p in case['trades']), 'Whole-position native net', 'cash', .00001)
        by_risk = {int(p['position_id']): p for p in risks}
        require(len(by_risk) == len(risks) == len(grouped) == len(case['trades']), 'Receipt/position coverage', 'risk')
        ordered = sorted(case['trades'], key=lambda p: (p['open_epoch'], p['position_id']))
        require(all(a['close_epoch'] <= b['open_epoch'] for a, b in zip(ordered, ordered[1:])),
                'Ambiguous same-EA floating ownership', 'ownership')
        excess = 0
        for p in case['trades']:
            require(begin <= p['open_epoch'] <= p['close_epoch'] < end, 'Source trade outside dates', 'coverage')
            parts = grouped[p['position_id']]
            opened = [d for d in parts if int(d['entry']) == 0]
            closed = [d for d in parts if int(d['entry']) == 1]
            require(len(opened) == len(closed) == 1 and not p['partial'], 'Partial or multiple entry unsupported', 'ownership')
            a, z, risk = opened[0], closed[0], by_risk[p['position_id']]
            require(risk['calculation_ok'] == risk['margin_ok'] == '1' and risk['sl_source'] == 'entry_order',
                    'Actual fill risk/margin unavailable', 'risk')
            close(float(a['volume']), p['volume'], 'Source volume', 'risk')
            close(float(a['price']), float(risk['entry_price']), 'Actual fill price', 'risk')
            close(float(a['sl']), float(risk['sl']), 'Original entry stop', 'risk')
            close(float(a['volume']), float(z['volume']), 'Whole exit volume', 'cash')
            require(abs(int(risk['epoch'])-p['open_epoch']) <= 1 and
                    abs(int(risk['quote_epoch'])-p['open_epoch']) <= 30, 'Contemporaneous entry receipt', 'risk')
            require(float(risk['unit_risk']) > 0 and float(risk['margin_one_lot']) >= 0,
                    'Invalid native unit quantities', 'risk')
            net = sum(float(d[k]) for d in parts for k in ('gross', 'commission', 'swap', 'fee'))
            close(net, p['net'], 'Position full net cash', 'cash')
            censored = any('end of test' in d['comment'].lower() for d in closed)
            require(p['end_censored'] == censored, 'Boundary liquidation classification', 'censoring')
            excess += float(risk['unit_risk'])*p['volume'] > 50.01
        trace = csv_rows(folder/'equity.csv')
        times = [int(p['epoch']) for p in trace]
        require(times == sorted(times) and times[0] == begin, 'Native equity sampling shifted/out of order', 'coverage')
        require(datetime.fromtimestamp(times[-1], timezone.utc).date().isoformat() == '2026-10-16',
                'Final completed day missing', 'coverage')
        opens = [p['open_epoch'] for p in ordered]
        boundaries = {p[k] for p in ordered for k in ('open_epoch', 'close_epoch')}
        owned = discarded_finish = 0
        for p in trace:
            stamp = int(p['epoch'])
            balance, equity = float(p['balance']), float(p['equity'])
            require(math.isfinite(balance) and math.isfinite(equity), 'Nonfinite sampled equity', 'ownership')
            if p.get('phase') == 'finish_after_native_liquidation':
                discarded_finish += 1
                continue
            require(p.get('phase') in (None, '', 'market_sample'), 'Unknown equity observation phase', 'ownership')
            if stamp in boundaries:
                continue
            i = bisect_left(opens, stamp)-1
            if i >= 0 and ordered[i]['open_epoch'] < stamp < ordered[i]['close_epoch']:
                owned += 1
            else:
                require(abs(equity-balance) < .021, 'Unowned floating native sample', 'ownership')
        coverage = csv_rows(folder/'coverage.csv')
        require(len(coverage) == 1 and int(coverage[0]['m1_first']) >= begin and
                begin < int(coverage[0]['m1_last']) < end and int(coverage[0]['m1_count']) > 0,
                'M1 source coverage', 'coverage')
        contracts = csv_rows(folder/'contracts.csv')
        require(len(contracts) == 1 and int(contracts[0]['account_leverage']) == 2000,
                'Source contract receipt', 'coverage')
        summaries.append(dict(slug=slug, positions=len(ordered), net_profit=round(cash_net, 2),
            history_quality=case['native']['history_quality'], equity_samples=len(trace), owned_samples=owned,
            discarded_post_liquidation_observations=discarded_finish,
            native_fill_risk_over_50_count=excess, censored=sum(p['end_censored'] for p in ordered),
            nonfatal_native_order_flags={key: value for key, value in case['flags'].items() if value}))
    output = dict(status='PASS', checks=sum(CHECKS.values()), categories=dict(CHECKS), cases=summaries,
        native_index_sha256=sha(ROOT/'native_cases.json'), source_freeze_sha256=sha(ROOT/'FROZEN.json'),
        resume_freeze_sha256=sha(ROOT/'RESUME FREEZE.json'), verifier_sha256=sha(__file__),
        export_v3_freeze_sha256=sha(ROOT/'EXPORT V3 FREEZE.json'),
        continuation_freeze_sha256=sha(ROOT/'CONTINUATION FREEZE.json'),
        method='Independent read-only CSV/receipt/frozen-graph/private-server-provenance audit; no trading replay imported or account access.',
        limitations=['Standalone native sources, not simultaneous shared-account portfolio execution.',
            'Current client minimum-lot override can exceed selected cash risk; current historical source costs are not guaranteed current-demo/live costs.',
            'Later shared-account signal changes after rejections and intrabar equity extremes are outside these source samples.'])
    (ROOT/'SOURCE VERIFICATION.json').write_text(json.dumps(output, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()

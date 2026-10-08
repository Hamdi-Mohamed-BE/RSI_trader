"""Requested TP-only native comparison. No search, deployment or live-account API."""
from pathlib import Path
import hashlib, html, importlib.util, json, msvcrt, os, re, subprocess

ROOT = Path(__file__).resolve().parent
R = ROOT / 'Agent3010'
B = ROOT.parent
OLD = B / 'US100 H1 ORB Optimization 2026-10-06'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
spec = importlib.util.spec_from_file_location('orb_requested_comparison', OLD / 'native.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
PORT = 3010
ORIGINAL_POPEN = subprocess.Popen

def free_independent_agent():
    """Read-only availability checks; never stops another process."""
    cmd = "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    processes = subprocess.run(['powershell', '-NoProfile', '-Command', cmd],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert str(n.T).lower() not in processes.stdout.lower(), 'Isolated terminal occupied'
    ports = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True,
        text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    assert not any(f':{PORT} ' in line and 'LISTENING' in line for line in ports.splitlines()), 'Independent tester port occupied'

def launch_with_independent_agent(*args, **kwargs):
    """Add the documented Tester Port only to this comparison's generated config."""
    command = args[0] if args else kwargs.get('args', '')
    if isinstance(command, str) and command.startswith('"'+str(n.T/'terminal64.exe')+'"'):
        match = re.search(r'/config:"([^"]+)"', command)
        assert match, 'Unexpected owned tester launch'
        config = Path(match.group(1)).resolve()
        assert config.is_relative_to(R.resolve()) and config.name == 'tester.ini'
        body = config.read_text(encoding='utf-8-sig')
        assert '[Tester]\n' in body and not re.search(r'^Port=', body, re.M)
        config.write_text(body.replace('[Tester]\n', f'[Tester]\nPort={PORT}\n', 1), encoding='utf-8-sig')
        free_independent_agent()
    return ORIGINAL_POPEN(*args, **kwargs)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def freeze():
    files = [n.BASE, n.ORIGINAL, n.ORIGINAL.with_suffix('.mq5'),
             B / '_Shared/CalyxAdaptivePortfolio.mqh',
             B / '_Shared/CalyxORBComments.mqh',
             B / '_Auto Deploy/Install-BMTradingPortfolio.ps1',
             OLD / 'native.py', OLD / 'parity.json', Path(__file__),
             *sorted((OLD / 'EA').glob('*.mq*'))]
    value = {'files': {str(p.relative_to(B)): sha(p) for p in files}}
    target = R / 'frozen.json'
    if target.exists():
        assert n.read(target) == value, 'Frozen comparison inputs changed'
    else:
        n.save(target, value)
    return value

def setup():
    build = n.read(OLD / 'build.json')
    assert sha(n.SOURCE.with_suffix('.ex5')) == build['binary']
    assert sha(n.ORIGINAL) == build['frozen']['production'][str(n.ORIGINAL.relative_to(B))]
    assert sha(n.BASE) == build['frozen']['production'][str(n.BASE.relative_to(B))]
    assert n.read(OLD / 'parity.json')['exact_entry_exit_volume_cost_parity']
    for p in (OLD / 'EA').glob('*.mq*'):
        assert sha(p) == build['frozen']['research'][p.name], 'Audited source changed'
    # Reuse the previously production-parity-verified audit binary and helpers.
    # Do not resume or mutate the paused optimisation or its OOS protocol.
    n.R = R
    n.freeze = freeze
    n.h.free = free_independent_agent
    n.g.h.h.free = free_independent_agent
    n.subprocess.Popen = launch_with_independent_agent
    frozen = freeze()
    n.save(R / 'build.json', {'binary': build['binary'], 'frozen': frozen,
           'provenance': str(OLD / 'build.json'), 'no_recompile': True})
    n.save(R / 'PLAN.json', {
        'symbol': 'USTEC (Exness US100)', 'signal_timeframe': 'M15',
        'opening_range_minutes': 60, 'from': '2025-10-06',
        'end_exclusive': '2026-10-06', 'deposit_usd': 10000,
        'risk_percent_equity': 1, 'model': 4, 'execution_delay_ms': 150,
        'variants': {'Current': 6.0, 'Requested': 0.5},
        'only_strategy_input_difference': 'InpRewardRisk',
        'independent_local_agent_port': PORT,
        'no_optimisation': True, 'no_live_changes': True,
        'note': 'Retrospective one-year diagnostic, not untouched final OOS.'})

def render(summary):
    labels = [
        ('Trades', 'trades', 0), ('Win rate %', 'win_rate', 2),
        ('Profit factor', 'pf', 2), ('Return %', 'return_pct', 2),
        ('Maximum equity drawdown %', 'equity_dd_pct', 2),
        ('Annualized daily-equity Sharpe', 'sharpe_daily_equity', 2),
        ('Maximum winning streak', 'win_streak', 0),
        ('Maximum losing streak', 'loss_streak', 0),
        ('Average winner USD', 'avg_win', 2),
        ('Average loser USD', 'avg_loss', 2),
        ('Average trades/month', 'trades_month', 2)]
    rows = []
    for label, key, places in labels:
        values = [summary['variants'][kind]['metrics'][key] for kind in ['current', 'rr05']]
        cells = [f'{value:,.{places}f}' if value is not None else 'N/A' for value in values]
        rows.append('<tr><td>'+html.escape(label)+'</td>'+''.join('<td>'+v+'</td>' for v in cells)+'</tr>')
    body = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>US100 H1 ORB — 6R versus 0.5R</title>
<style>body{background:#071512;color:#e9faf3;font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px}h1{font-size:28px}p{line-height:1.65;color:#abc7bd}table{border-collapse:collapse;width:100%;background:#10251e}th,td{text-align:right;padding:13px;border-bottom:1px solid #29483a}th:first-child,td:first-child{text-align:left}th{color:#71ffd0}.note{border:1px solid #8b733d;padding:16px;border-radius:10px}</style>
<h1>US100 H1 ORB: current 6R versus requested 0.5R</h1>
<p>Completed native comparison: 6 October 2025–5 October 2026 inclusive (6 October 2026 end-exclusive). Exness USTEC, M15 breakout confirmation, unchanged 60-minute opening range, $10,000 starting balance and 1% requested equity risk per trade. Only the reward/risk target changes.</p>
<table><thead><tr><th>Metric</th><th>Current 6R</th><th>Requested 0.5R</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table>
<p>Same structural stop, filters, one-trade-per-day rule and 20:00 UTC timed exit. No break-even or trailing added. Native costs and 150 ms execution delay included. Win rate and streaks use whole-position net profit including costs; daily-equity Sharpe is annualized using 252 weekdays and a zero risk-free rate, not MT5's separately reported Sharpe.</p>
<p class="note">Research only. The one-year native report contains 76% real ticks: real-tick history starts 1 January 2026, so earlier dates include generated ticks. This is not an untouched out-of-sample claim. Requested 1% risk is not a guaranteed loss cap: slippage and gaps can exceed it. Live EAs, BATs, website and settings remain unchanged.</p>
<p>Complete native reports, inputs, audited trades and equity traces are retained alongside this page.</p></html>'''
    (R / 'Results.html').write_text(body, encoding='utf-8')

def main():
    with (B / 'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0)
        msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        setup()
        a = n.run('rrcomp20261008-current-1y', '1y', model=4)
        b = n.run('rrcomp20261008-half-1y', '1y', {'InpRewardRisk': 0.5}, model=4)
        differences = [k for k in a['inputs'] if a['inputs'][k] != b['inputs'].get(k)
                       and k != 'InpAuditTag']
        assert differences == ['InpRewardRisk'], differences
        assert not a['operational_failure'] and not b['operational_failure']
        assert a['binary_sha256'] == b['binary_sha256']
        identities = lambda q: [(t['open_epoch'], t['side']) for t in q['trades']]
        paired = identities(a) == identities(b)
        variants = {}
        for key, q in [('current', a), ('rr05', b)]:
            metrics = dict(q['metrics'], equity_dd_pct=q['native']['equity_dd_pct'])
            variants[key] = {'metrics': metrics, 'native': q['native'],
                'report': str(R / 'native' / q['tag'] / 'report.htm'),
                'tick_notes': q['tick_notes'], 'flags': q['flags']}
        summary = {'plan': n.read(R / 'PLAN.json'), 'variants': variants,
                   'identical_entry_times_and_directions': paired,
                   'input_differences_excluding_audit_tag': differences,
                   'production_files_unchanged': freeze() == n.read(R / 'frozen.json')}
        n.save(R / 'SUMMARY.json', summary)
        render(summary)
        n.save(R / 'VERIFICATION.json', {'native_money_and_deal_reconciliation': True,
            'native_inputs_verified': True, 'same_binary': True,
            'identical_entries': paired, 'production_unchanged': True,
            'test_windows_match': a['window'] == b['window'],
            'no_optimization_or_deployment': True})
        print('COMPARISON COMPLETE', json.dumps(summary), flush=True)

if __name__ == '__main__':
    main()

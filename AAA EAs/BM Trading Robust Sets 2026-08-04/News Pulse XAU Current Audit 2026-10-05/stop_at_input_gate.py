"""Finish recent diagnostics, abort ONLY this study's older-history owned replay.

The frozen protocol forbids promotion/optimisation on unproven event-time ticks.
Do not spend further runs on older generated news paths. No live terminal control.
The already-running frozen batch has no stop-file hook, so this external guard
terminates its exclusively owned 3Y diagnostic at startup and records it as
ABORTED, never as a completed backtest. The 5Y case is NOT RUN.
"""
from pathlib import Path
import json, subprocess, time
R=Path(__file__).resolve().parent;B=R.parent
T=B/'_Backtests/MT5-DMC-20260811/terminal64.exe'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def main():
 year=read(R/'native/1Y-150/results.json')
 assert 'real ticks begin from 2026.01.01 00:00:00' in year['tick_notes']
 assert year['native']['history_quality']=='75% real ticks'
 guard={'basis':'Frozen input-quality stop, not selection by profit','real_tick_start':'2026-01-01T00:00:00Z','older_seconds_long_news_price_paths_unproven':True,'optimisation_allowed':False,'references':['https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation','https://www.metatrader5.com/en/terminal/help/algotrading/testing'],'current_rules_unchanged':True}
 save(R/'INPUT GATE STOP.json',guard)
 deadline=time.monotonic()+3000
 while time.monotonic()<deadline:
  owned=R/'native/3Y-150/owned-process.json'
  if owned.exists() and all((R/f'native/{tag}/results.json').exists() for tag in ['1Y-1000','1Y-3000','6M-150','3M-150']):break
  time.sleep(2)
 else:raise RuntimeError('Guard deadline reached; no process was stopped')
 receipt=read(owned);assert Path(receipt['path']).resolve()==T.resolve()
 target_ini=R/'native/3Y-150/tester.ini'
 # Native PowerShell end-to-end; exact PID, executable, config and creation time.
 command=f'''$newsOwned = Get-CimInstance Win32_Process -Filter "ProcessId={int(receipt['pid'])}";
 if (!$newsOwned) {{throw 'Owned older replay is no longer running'}}
 if ($newsOwned.ExecutablePath -ne '{T}' -or !$newsOwned.CommandLine.Contains('{target_ini}')) {{throw 'Owned process identity mismatch; no process stopped'}}
 $newsStarted = ([DateTimeOffset]$newsOwned.CreationDate).ToUnixTimeSeconds();
 if ([math]::Abs($newsStarted - {receipt['started']}) -gt 5) {{throw 'PID was reused; no process stopped'}}
 Stop-Process -Id {int(receipt['pid'])} -ErrorAction Stop;
 Write-Output 'Only the owned older-history research replay was aborted at the input gate.'
 '''
 result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 print(result.stdout,flush=True)
 reason='Real ticks only start 2026-01-01; generated earlier event-second paths cannot qualify. Frozen input gate stops before optimisation.'
 skips=[dict(case='3Y-150',delay_ms=150,status='ABORTED at input-quality gate',completed_native_result=False,reason=reason,owned_process=receipt),dict(case='5Y-150',delay_ms=150,status='NOT RUN after input-quality stop',completed_native_result=False,reason=reason)]
 save(R/'NOT RUN.json',skips)
 save(R/'COMPLETE.json',dict(status='Recent diagnostic audit finished; stopped at input-quality gate',native_replays=8,uncompleted_older_cases=2,all_ten_performance_cases_completed=False,optimisation_performed=False,new_bat_created=False,production_changed=False))
 print('INPUT GATE: stop before optimisation. Older-window returns will not be fabricated.',flush=True)
if __name__=='__main__':main()

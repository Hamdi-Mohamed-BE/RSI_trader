"""Read-only, exact-terminal audit. No login, orders, changes, or terminal restart."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
import MetaTrader5 as mt5

ROOT=Path(__file__).resolve().parent
MAGIC=969060311
def save(name,value):
    (ROOT/name).write_text(json.dumps(value,indent=2,default=str),encoding='utf-8')
def main():
    assert mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe',timeout=10000),mt5.last_error()
    try:
        terminal=mt5.terminal_info(); account=mt5.account_info()
        assert terminal.path.lower()==r'C:\Program Files\MetaTrader 5'.lower()
        end=datetime.now(timezone.utc)
        deals=mt5.history_deals_get(datetime(2026,1,1,tzinfo=timezone.utc),end)
        assert deals is not None, mt5.last_error()
        ids={d.position_id for d in deals if d.magic==MAGIC and d.entry in (mt5.DEAL_ENTRY_IN,mt5.DEAL_ENTRY_INOUT)}
        selected=[d._asdict() for d in deals if d.position_id in ids]
        for d in selected:
            d['utc']=datetime.fromtimestamp(d['time'],timezone.utc).isoformat()
        positions=[p._asdict() for p in mt5.positions_get() or [] if p.magic==MAGIC]
        rows=[]
        for pid in sorted(ids):
            ds=sorted([d for d in selected if d['position_id']==pid],key=lambda d:d['time_msc'])
            ins=[d for d in ds if d['entry']==0]; outs=[d for d in ds if d['entry']==1]
            if not ins: continue
            vin=sum(d['volume'] for d in ins);vout=sum(d['volume'] for d in outs)
            net=sum(sum(d[k] for k in ('profit','swap','commission','fee')) for d in ds)
            rows.append(dict(position_id=pid,symbol=ins[0]['symbol'],entry=ins[0]['utc'],entry_epoch=ins[0]['time'],side='long' if ins[0]['type']==0 else 'short',volume=vin,exit=outs[-1]['utc'] if outs else None,exit_epoch=outs[-1]['time'] if outs else None,closed=abs(vin-vout)<1e-8,net=round(net,2),exit_reasons=[d['reason'] for d in outs],manual=any(d['reason'] in (0,1,2) for d in outs)))
        rows.sort(key=lambda r:r['entry_epoch'])
        for i,r in enumerate(rows):
            next_entry=next((n for n in rows[i+1:] if n['entry_epoch']>=(r['exit_epoch'] or 10**20)),None)
            r['next_entry_after_exit_minutes']=(next_entry['entry_epoch']-r['exit_epoch'])/60 if next_entry else None
            r['next_entry_same_side']=next_entry['side']==r['side'] if next_entry else None
        closed=[r for r in rows if r['closed']]
        summary=dict(asof=end.isoformat(),account_suffix=str(account.login)[-4:],broker=account.company,server=account.server,demo=account.trade_mode==0,currency=account.currency,terminal_build=terminal.build,terminal_data_path=terminal.data_path,magic=MAGIC,history_requested_from='2026-01-01',first_target_entry=rows[0]['entry'] if rows else None,entries=len(rows),closed_positions=len(closed),open_positions=len(positions),closed_net=round(sum(r['net'] for r in closed),2),manual_closed_positions=sum(r['manual'] for r in closed),exit_reason_mapping={'0':'desktop manual','1':'mobile manual','2':'web manual','3':'expert','4':'stop loss','5':'take profit'},rows=rows)
        save('account-audit.json',summary);save('account-target-deals.private.json',selected);save('account-target-open.private.json',positions)
        print(json.dumps(summary,indent=2))
    finally: mt5.shutdown()
if __name__=='__main__':main()

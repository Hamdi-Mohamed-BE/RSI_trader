"""Audit and publish longer portfolio evidence; pure offline, no MT5 API."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, sys

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
WEB=BASE.parent/'EA store'
sys.path.insert(0,str(WEB))
from app.portfolio_analytics import allocation_replay, history_from_trades
from app.portfolio_guard_replay import replay

START,END='2021-10-06','2026-10-06'
PERIODS=[('3m','3 months','2026-07-06'),('6m','6 months','2026-04-06'),
         ('1y','1 year','2025-10-06'),('3y','3 years','2023-10-06'),('5y','5 years',START)]
CONTRACTS={'XAUUSD':100.,'XAGUSD':5000.,'USDJPY':100000.,'EURUSD':100000.,
           'USTEC':1.,'US30':1.,'BTCUSD':1.,'ETHUSD':1.}


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def epoch(value):return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def boundary_liquidation(trade):
    return any('end of test' in comment.lower() for comment in trade['exit_comments'])


def rows(case,row):
    symbol=row['symbol'];slug=row['slug'];contract=CONTRACTS[symbol]
    results=[]
    for t in case['trades']:
        assert t['volume']>0 and epoch(START)<=t['open_epoch']<=t['close_epoch']<epoch(END)
        if boundary_liquidation(t):continue # Open at the boundary, not a strategy exit.
        hourly=slug.endswith('hourly-profiles')
        if hourly:
            assert t['sl']==0
            unit=float(row['input_settings']['InpHistoricalLossPoints'])*contract
        else:
            assert t['sl']>0, ('Missing initial stop',slug,t['position_id'])
            assert (t['sl']<t['open_price'])==(t['side']=='Long'), ('Initial stop geometry',slug,t['position_id'])
            unit=abs(t['open_price']-t['sl'])*contract/(t['sl'] if symbol=='USDJPY' else 1.)
        assert unit>0
        results.append(dict(key=slug,symbol=symbol,news=slug.startswith('news-pulse-'),
            op=t['open_epoch'],cl=max(t['close_epoch'],t['open_epoch']+.001),position_id=t['position_id'],
            unit_risk=unit,unit_gross=t['gross']/t['volume'],unit_comm=(t['commission']+t['fee'])/t['volume'],
            unit_swap=t['swap']/t['volume'],open_price=t['open_price'],close_price=t['close_price'],side=t['side'],
            lane=str(t['magic']) if slug=='3-way-gold' else slug,partial=t['partial'],
            order_compatible=slug!='xau-weakness',risk_weight=.5 if slug=='xau-weakness' else 1.,
            risk_reference='frozen historical maximum loss; NO STOP' if hourly else 'filled initial stop'))
    return results


def portfolio_evidence(plan,state,slug):
    index={r['case_id']:r for r in plan['cases']}
    pooled=[];missing=[];sources=[]
    for key,case_id in plan['mappings'][slug].items():
        if case_id not in state['complete']:
            missing.append(dict(slug=key,reason=state['missing'].get(case_id,state['failed'].get(case_id,{}).get('error','Test still pending'))))
            continue
        receipt=state['complete'][case_id];path=Path(receipt['path'])
        assert sha(path)==receipt['sha256']
        case=read(path)
        assert case['window']==['2021.10.06','2026.10.06'] and case['no_live_changes']
        try:
            pooled.extend(rows(case,index[case_id]))
        except AssertionError as error:
            missing.append(dict(slug=key,reason=str(error)))
            continue
        sources.append(dict(slug=key,case_id=case_id,sha256=receipt['sha256'],native_trades=len(case['trades']),
            excluded_boundary_positions=sum(boundary_liquidation(t) for t in case['trades']),
            history_quality=case['native']['history_quality'],flags=case['flags'],tick_notes=case['tick_notes'],
            calendar_audit=case.get('calendar_audit')))
    # Do not silently omit a strategy merely because its genuine native test has zero trades.
    assert len(sources)+len(missing)==len(plan['mappings'][slug])
    return pooled,missing,sources


def histories(slug,rows,missing,sources):
    output=[]
    for period,title,start in PERIODS:
        begin,finish=epoch(start),epoch(END)
        eligible=[dict(r) for r in rows if begin<=r['op']<r['cl']<finish]
        if slug=='ftmo':
            result=replay(eligible,[],begin,finish,challenge=False,detail=True)
            trades=[dict(slug=t['ea'],position_id=i,close_time=t['close'],net_profit=t['net_profit']) for i,t in enumerate(result['log'])]
            info=dict(skips=result['counts'],guard_proxy_breach=result['breach'],max_daily_stop_reserve_loss_cash=result['worst_daily_usd'],
                unclosed_positions=result['open_positions'],last_admitted_entry=max((t['open'] for t in result['log']),default=None))
            basis='Fixed $50 / $10,000; fresh offline FTMO admission-guard replay.'
        else:
            full=slug=='full-eas'
            trades,info=allocation_replay(eligible,start,END,'fixed',25 if full else 50,10000,
                adaptive=full,news_percent=.10)
            basis=('Fixed $25 non-news / 0.10% news, adaptive entry replay on $10,000.' if full
                   else 'Fixed $50 initial-stop risk, fractional-lot entry replay on $10,000.')
        quality=sorted(set(s['history_quality'] for s in sources))
        execution_warnings={s['slug']:{k:s['flags'][k] for k in ('invalid_stops','invalid_volume') if s['flags'].get(k)}
            for s in sources if any(s['flags'].get(k) for k in ('invalid_stops','invalid_volume'))}
        calendar_audits={s['slug']:s['calendar_audit'] for s in sources if s.get('calendar_audit')}
        scope=('Matched current strategy settings; frozen membership, no re-selection or optimization. '
            'Research overlay of separate five-year native MT5 tests, not a native simultaneous shared-margin portfolio. '
            'Each selected window replays sizing/guards from a fresh balance and excludes carry-in/carry-out positions. '
            'MT5 end-of-test liquidations are excluded from these closed-trade replays. '
            'The 3-year/recent views are slices/replays of the five-year signal ledger, not independent native tests. '
            'Source real-tick coverage varies: '+', '.join(quality)+'. MT5 may synthesize unavailable earlier ticks. '
            'Partial exits/costs are collapsed at final close. Intratrade floating equity, shared margin, lot rounding and rejected-entry retries are not reconstructed. ')
        if slug=='ftmo':
            scope+='Saved admission guard, rounded lots and stop-reserve equity proxy; NOT measured floating equity or a calibrated funding forecast. This is one continuous account, not rolling challenges or restart-after-failure simulations; challenge phase targets are not simulated. '
            if info['skips'].get('total_loss_buffer_rejected'):
                scope+='The unchanged $9,200 buffer blocked '+str(info['skips']['total_loss_buffer_rejected'])+' later entries; last admitted entry '+str(info['last_admitted_entry'])+'. A shorter window starts with a fresh $10,000 and can therefore have very different results. '
        if slug=='full-eas':
            scope+='Approximate adaptive closed-balance controls; dynamic sizing uses closed balance, not floating equity. Hourly risk uses the unchanged annual historical-loss reference; NO protective stop. News uses the official-source receipted schedule, not a point-in-time calendar vintage. '
            scope+='A tester-only, native-parity-verified cached calendar lookup preserves timer cadence and all trading rules; production news sources are unchanged. '
            scope+='Sub-minute news results are especially sensitive to generated ticks and are NOT a full real-tick execution validation. '
            scope+='Sizing is normalized from filled initial-stop distance, not reconstructed from pending-order placement-time risk; tiny/gap-shifted stop distances can exaggerate normalized outcomes. '
            scope+='XAU Weakness retains its two-order allocation: half the selected idea budget per filled order. '
        if missing:scope+='Incomplete basket: '+str(len(sources))+'/'+str(len(sources)+len(missing))+' current members tested. Missing members are NOT assigned zero P/L. '
        if execution_warnings:scope+='Some native journals report rejected stops/volumes; only actual native fills are replayed, not idealized successful entries or trailing updates. Journal message counts are not unique rejected-trade counts. '
        h=history_from_trades(trades,start,END,period,title+' · '+('partial current basket' if missing else 'matched long-history replay'),basis,scope,[m['slug'] for m in missing])
        h.update(coverage='partial' if missing else 'complete',scenario=info,member_coverage=dict(tested=len(sources),total=len(sources)+len(missing)),
            evidence_kind='matched-five-year-native-signal-ledger-offline-portfolio-replay',source_history_quality=quality,
            source_execution_warnings=execution_warnings,
            source_calendar_audits=calendar_audits,
            source_boundary_exclusions={s['slug']:s['excluded_boundary_positions'] for s in sources if s['excluded_boundary_positions']})
        if slug=='ftmo':h['stats']['max_daily_stop_reserve_loss_cash']=info['max_daily_stop_reserve_loss_cash']
        output.append(h)
    return output


def main():
    plan=read(ROOT/'PLAN.json');state=read(ROOT/'RUN_STATUS.json')
    expected={r['case_id'] for r in plan['cases']}
    finished=set(state['complete'])|set(state['missing'])|set(state['failed'])
    assert finished<=expected
    result={};risk={};audits={}
    for slug in plan['mappings']:
        if not set(plan['mappings'][slug].values())<=finished:
            continue # Pending tests are not a historical coverage gap or zero P/L.
        pooled,missing,sources=portfolio_evidence(plan,state,slug)
        if not sources:continue
        # Partial publication is deliberate and explicit; failed/untestable members are not zero P/L.
        result[slug]=histories(slug,pooled,missing,sources)
        risk[slug]=pooled
        audits[slug]=dict(missing=missing,sources=sources,membership_fixed=True)
    write(ROOT/'HISTORIES.json',result)
    (ROOT/'RISK_ROWS.json').write_text(json.dumps(risk,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    write(ROOT/'AUDIT.json',dict(window=[START,END],portfolios=audits,production_files_unchanged=all(sha(p)==v for r in plan['cases'] for p,v in r['production_hashes'].items()),
        native_simultaneous_portfolio=False,live_changes=False,selection_frozen=True,
        pending_cases=len(expected-finished),ready_profiles=sorted(result)))
    print(json.dumps({s:dict(coverage=h[-1]['coverage'],members=h[-1]['member_coverage'],stats=h[-1]['stats']) for s,h in result.items()},indent=2))


if __name__=='__main__':main()

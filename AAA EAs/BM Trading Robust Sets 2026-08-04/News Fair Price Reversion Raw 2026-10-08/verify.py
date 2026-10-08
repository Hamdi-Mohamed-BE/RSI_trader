"""Independent post-run ledger, chronology and reporting checks; never trades."""
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
import gzip, json, math, re, subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import audit as a

checks = 0
def check(condition, context):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(context)

def near(actual, expected, tolerance, context):
    check(abs(actual-expected) <= tolerance, (context, actual, expected))

def xml_cash(path):
    ns = {'s':'urn:schemas-microsoft-com:office:spreadsheet'}
    header = None
    results = {}
    for row in ET.parse(BytesIO(gzip.decompress(path.read_bytes()))).getroot().findall('.//s:Row', ns):
        values=[]
        for cell in row.findall('s:Cell',ns):
            index=cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if index:
                values += ['']*max(0,int(index)-1-len(values))
            data=cell.find('s:Data',ns)
            values.append(''.join(data.itertext()) if data is not None else '')
        if 'Pass' in values and 'InpCase' in values:
            header=values
        elif header and len(values)==len(header):
            d=dict(zip(header,values))
            if d.get('InpCase','').isdigit():
                results[int(d['InpCase'])]=float(d['Profit'].replace(' ',''))
    check(set(results)=={0,1},'Exactly two frozen native cases')
    return results

def main():
    frozen=json.loads((a.R/'FROZEN.json').read_text())
    for name,field in [('config.json','config_sha256'),('engine.mq5','engine_sha256'),('build_engine.py','build_sha256'),('calendar.json','calendar_sha256')]:
        check(a.sha(a.R/name)==frozen[field], 'Post-freeze mutation: '+name)
    check(frozen['cases']==[{'allow_longs':0},{'allow_longs':1}] and not frozen['optimisation'], 'No selected or tuned case')
    ev=a.CALENDAR['events']
    check(len(ev)==31 and Counter(x['kind'] for x in ev)=={'CPI':11,'NFP':12,'FOMC':8},'Calendar counts')
    check([e['epoch'] for e in ev]==sorted(set(e['epoch'] for e in ev)), 'Unique sorted releases')
    for e in ev:
        local=datetime.fromtimestamp(e['epoch'],timezone.utc).astimezone(a.NY)
        check((local.hour,local.minute)==((14,0) if e['kind']=='FOMC' else (8,30)), 'Calendar NY/DST '+e['release_utc'])
        check(a.stamp(e['epoch'])==e['release_utc'], 'Calendar UTC epoch matches receipt')
    source=(a.R/'engine.mq5').read_text()
    for guard in ['!MQLInfoInteger(MQL_TESTER)','b.time+60>now','pivot_confirm<=b.time','pre_atr=values[0]','ep+(dir>0?-1:1)*2*pre_atr','MathFloor(budget/-loss/step','filled+3600','Events[event_index]+5400']:
        check(guard in source,'Frozen causal/risk source guard '+guard)
    summary=json.loads((a.R/'SUMMARY.json').read_text())
    all_rows={}
    for key,row in a.RESULTS.items():
        native=row['native']
        folder=a.R/'native'/row['stage']
        manifest=json.loads((folder/'manifest.json').read_text())
        check(manifest['config_sha256']==frozen['config_sha256'],'Native config frozen')
        check(manifest['cases']==frozen['cases'],'Native cases frozen')
        check(manifest['model']==4 and manifest['risk']==1 and manifest['delay']==150,'Native settings')
        check(manifest['start']==a.C['start'] and manifest['end']==a.C['end_exclusive'],'Native window')
        check(a.sha(folder/'OrbSearch.ex5')==row['binary_sha256'],'Binary receipt')
        import hashlib
        # The manifest hashes the UTF-8 generated text before Windows writes
        # native CRLF line endings. Normalise only line endings for this hash;
        # all bytes of the compiled binary and compressed report remain checked.
        generated=(folder/'OrbSearch.mq5').read_text(encoding='utf-8')
        check(hashlib.sha256(generated.encode()).hexdigest()==manifest['engine_sha256'],'Generated source text receipt (LF normalized)')
        check((folder/'report.xml.gz').stat().st_mtime >= datetime.fromisoformat(frozen['created_utc']).timestamp(), 'Fresh post-freeze native report')
        report_raw=gzip.decompress((folder/'report.xml.gz').read_bytes())
        check(hashlib.sha256(report_raw).hexdigest()==row['report_sha256'],'Native XML receipt')
        raw=a.csv(row,'deals')
        net=float(raw[['profit','commission','swap','fee']].to_numpy().sum())
        profits=xml_cash(folder/'report.xml.gz')
        near(net,profits[row['index']],.011,'Deals reconcile native XML')
        near(net,native['net'],.011,'Deals reconcile native statistics')
        near(native['balance'],10000+net,.011,'Terminal final balance')
        check(native['open_position']==0 and native['failed_entries']==0 and native['failed_updates']==0 and native['market_closed_updates']==0,'No unfinished/rejected execution')
        item=summary[key]
        trades=item['trades']; m=item['metrics']
        near(net,m['net_usd'],1e-7,'Report money')
        near(net/100,m['return_pct'],1e-9,'Return base')
        near(m['max_floating_dd_pct'],native['equity_dd'],1e-9,'Report DD uses native full-tick statistic')
        check(len(trades)==len(raw[raw.entry==0])==int(native['trades'])==m['trades'],'Native position counts')
        check(set(raw.entry).issubset({0,1}), 'No unsupported reversal/partial lifecycle')
        d=a.csv(row,'decisions')
        entry=d[d.reason.isin(['entry_displacement','entry_structure'])]
        check(entry.event_index.is_unique, 'One trade per release')
        check(len(entry)==len(trades),'All entry decisions matched')
        first=d[d.reason=='event_start']
        missing=d[d.reason=='no_tradable_event_window']
        check(set(first.event_index)|set(missing.event_index)==set(range(31)),'All calendar events classified')
        check(len(first)==native['events_seen'],'Events started native count')
        for _,record in first.iterrows():
            check(record.bar_epoch==record.event_epoch-60,'Exact pre-news candle')
            near(record.close,record.fair,1e-7,'Bid-close reference price')
            check(record.epoch>=record.event_epoch and record.pre_atr>0,'ATR frozen after causal pre-event history available')
        for t in trades:
            dt=entry[(entry.epoch-t['open_epoch']).abs()<=1]
            check(len(dt)==1,'Native fill uniquely matches decision')
            z=dt.iloc[0]; idx=int(z.event_index); event=ev[idx]
            check(z.kind==event['kind'] and z.event_epoch==event['epoch'],'Native event matches receipt')
            check(t['event']==event['kind'] and t['event_epoch']==event['epoch'],'Reported event correct')
            check(event['epoch']+120 <= t['open_epoch'] < event['epoch']+1800,'Entry causal / within window')
            check(z.bar_epoch+60<=z.epoch and z.bar_epoch>=event['epoch']+60,'Signal candle completed')
            check(t['side']==('sell' if z.spike==1 else 'buy'),'Reversion direction')
            check(row['parameters']['allow_longs']==1 or t['side']=='sell','Main version short only')
            check(z.spike in [-1,1] and (z.first_news_close-z.fair)*z.spike>=z.pre_atr-1e-8,'Initial impulse threshold')
            st=first[first.event_index==idx]
            check(len(st)==1,'Pre-event reference present')
            near(z.fair,float(st.iloc[0].fair),1e-8,'Target frozen')
            near(z.pre_atr,float(st.iloc[0].pre_atr),1e-8,'ATR frozen')
            near(t['initial_sl'],float(z.sl),1e-7,'Broker SL matches request')
            near(t['initial_tp'],float(z.tp),1e-7,'Broker TP matches request')
            near(float(z.tp),float(z.fair),1e-7,'TP is pre-news target')
            check(t['initial_sl']>t['open_price']>t['initial_tp'] if t['side']=='sell' else t['initial_sl']<t['open_price']<t['initial_tp'],'SL/TP direction after fill')
            near(t['volume'],float(z.lots),1e-8,'Lots match request')
            check(z.lots*z.unit_loss <= z.risk_budget+1e-7, 'Floored planned stop risk within budget')
            prior=sum(x['net_profit'] for x in trades if x['close_epoch']<t['open_epoch'])
            near(z.risk_budget,(10000+prior)*.01,.00011,'One percent current account budget')
            check(0 <= t['close_epoch']-t['open_epoch'] <= 3600,'No hold beyond sixty minutes')
            check(t['close_epoch']<=event['epoch']+5400,'No hold beyond event deadline')
            check(datetime.fromtimestamp(t['open_epoch'],timezone.utc).date()==datetime.fromtimestamp(t['close_epoch'],timezone.utc).date(),'No overnight position')
            if z.reason=='entry_displacement':
                body=abs(z.close-z.open); span=z.high-z.low
                check(span>0 and body >= .5*z.pre_atr-1e-7 and body/span >= .6-1e-8,'Displacement strength')
                check((z.close<z.open and (z.close-z.low)/span<=.25+1e-8) if z.spike==1 else (z.close>z.open and (z.high-z.close)/span<=.25+1e-8),'Displacement reversal close')
            else:
                check(z.pivot>0 and z.pivot_epoch>=event['epoch'] and z.pivot_confirm<=z.bar_epoch,'Pivot known before breakout candle')
                check(z.close<z.pivot if z.spike==1 else z.close>z.pivot,'Close crosses pivot in reversal direction')
                piv=d[(d.event_index==idx)&(d.reason=='pivot_confirmed')&(d.pivot_epoch==z.pivot_epoch)]
                check(len(piv)>=1 and int(piv.iloc[-1].epoch)<=z.epoch,'Confirmed pivot log predates entry')
            group=raw[raw.position_id==t['position_id']]
            near(group[group.entry==0].volume.sum(),group[group.entry==1].volume.sum(),1e-8,'Position completely closed')
            near(group[['profit','commission','swap','fee']].to_numpy().sum(),t['net_profit'],1e-8,'Individual net fees reconciled')
        daily,sh=a.daily_curve(row)
        near(daily.iloc[-1].balance,native['balance'],.011,'Equity report endpoint')
        near(sh,m['daily_equity_sharpe'],1e-9,'Daily Sharpe recalculation')
        check(item['daily_curve'][-1]['date']=='2026-10-06','No fabricated October 7 observation')
        p=[t['net_profit'] for t in trades]
        near(m['pf'],a.pf(p),1e-9,'PF independently recalculated')
        near(m['win_rate_pct'],sum(v>0 for v in p)/len(p)*100,1e-9,'Win rate independently recalculated')
        check((m['win_streak'],m['loss_streak'])==a.streaks(p),'Win/loss streaks recomputed')
        for kind,gs in item['event_groups'].items():
            eventvalues=[t['net_profit'] for t in trades if t['event']==kind]
            near(sum(eventvalues),gs['net_usd'],1e-8,'Event cash contribution')
            check(len(eventvalues)==gs['trades'],'Event trade count')
        near(sum(x['net_usd'] for x in item['events']),net,1e-8,'31-event disposition ledger cash')
        q=a.coverage(row)
        check(q==item['quality'],'Quality recalculated from journal and quotes')
        check(any('2026.01.01' in x for x in q['real_tick_archive_starts']),'Fallback tick-history disclosure')
        for stress in item['cost_sensitivity']:
            extra=stress['extra_cost_r_per_trade']
            cash=[t['net_profit']-extra*t['risk_budget_usd'] for t in trades]
            near(sum(cash),stress['net_usd'],1e-8,'Added cost sensitivity cash')
        all_rows[key]=dict(trades=len(trades), calendar_dispositions=31,
                           skipped_no_quote_events=len(missing), native_cash_reconciled=True,
                           maximum_hold_minutes=m['maximum_hold_minutes'],
                           all_2026_entry_quotes_zero_spread=q['all_2026_entry_quotes_zero_spread'],
                           research_only=True, live_promotion=False)
    report=(a.R/'Results.html').read_text(encoding='utf-8')
    check(report.lower().count('<svg ')==4,'Four separate-asset charts')
    check(report.count('<details')==18 and report.count('</details>')==18,'Trade/event disclosures present')
    check(report.count('<table>')==report.count('</table>'),'HTML tables structurally complete')
    for key,item in summary.items():
        check(f"{item['metrics']['return_pct']:+.2f}%" in report,'Rendered return present')
        check(f"{item['metrics']['pf']:.2f}" in report,'Rendered PF present')
    check('zero bid/ask spread' in report and 'generated ticks' in report,'Execution limitations prominent')
    repo=a.R.parents[2]
    state=subprocess.run(['git','status','--short','--untracked-files=no'],cwd=repo,capture_output=True,text=True,check=True).stdout.strip()
    check(not state,'Tracked live/repository files unchanged')
    output=dict(verified_utc=datetime.now(timezone.utc).isoformat(), checks=checks,
                arithmetic_and_recorded_chronology_pass=True, source_settings_calendar_unchanged=True,
                native_deals_xml_statistics_cash_reconciled=True, no_overnight_positions=True,
                no_rejected_entries_or_time_closes=True, live_changes=False,
                rows=all_rows,
                limitations=[
                    'Chronology checks use saved native decisions and source guards; this is not a second independent full tick-engine implementation.',
                    'Pivot prior-close and ATR values originate in the native engine; audit confirms recorded readiness/freeze and guards, not an independent historical-price reconstruction.',
                    'Request-price-to-stop sizing is checked using native OrderCalcProfit cash risk. Decision bid/ask are sampled after send; 150ms fill movement means request price cannot be reconstructed exactly from these quote samples.',
                    'All 2026 EURUSD/BTCUSD entry quotes and most USTEC entry quotes have zero bid/ask spread. Gold has one such entry per version. All 2025 ticks are generated fallback. Data quality is not live-execution validation.',
                    'Added-cost sensitivity only subtracts assumed cash penalties from recorded trades; lots and paths are not rerun.',
                    'HTML numerical/structure checks performed. Browser rendering was not inspected because local file access was blocked.',
                    'Not a full pipeline or untouched out-of-sample test. No live promotion.'
                ])
    a.save('VERIFICATION.json',output)
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()

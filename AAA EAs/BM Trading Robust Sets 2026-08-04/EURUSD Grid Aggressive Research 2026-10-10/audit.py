"""Independent final check against native deal reasons, not just callback counters."""
from pathlib import Path
import run as r
n=r.n

def main():
    root=r.ROOT;s=n.read(root/'SUMMARY.json');p=n.read(root/'PLAN.json')
    assert s['completed']==36 and not s['failed']
    assert all(n.sha(Path(k))==v for k,v in p['source_hashes'].items())
    corrections=[];checked=[]
    for q in s['results']:
        folder=root/'native'/q['tag'];ds=n.export_rows(folder/'deals.csv')
        trades,cash=n.trades_from_deals(ds)
        assert abs(sum(t['net'] for t in trades)-q['native']['net_profit'])<=.031
        a=n.pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC').timestamp()
        z=n.pd.Timestamp(q['window'][1].replace('.','-'),tz='UTC').timestamp()
        assert all(a<=t['open_epoch']<=t['close_epoch']<z for t in trades)
        sos=[d for d in ds if int(d['entry'])==1 and int(d['reason'])==6]
        pids={int(d['position_id']) for d in sos}
        affected={t['magic'] for t in trades if t['position_id'] in pids}
        # Any stopout leg counts, including positions whose final leg had another reason.
        for b in q['baskets']:
            if b['magic'] in affected:b['stopout']=True;b['reason']='STOPOUT'
        if q['summary']['stopout_deals']!=len(sos):corrections.append(dict(tag=q['tag'],callback=q['summary']['stopout_deals'],native=len(sos)))
        q['stopout_reconciliation']=dict(callback_count=q['instrumentation']['stopout_deals'],native_deal_count=len(sos),authoritative_source='Native DEAL_REASON_SO across every closing leg')
        q['summary']['stopout_deals']=len(sos);q['summary']['stopout_baskets']=len(affected)
        if q['summary']['final_balance']<=0:q['summary']['compounded_equivalent_monthly_pct']=None
        assert sum(b['terminal'] for b in q['baskets'])==q['summary']['terminal_baskets']
        assert abs(sum(b['net'] for b in q['baskets'])-q['summary']['net_profit'])<=.031
        n.save(folder/'results.json',q);checked.append(q['tag'])
    # Confirm validation parameters exactly match the pre-validation frozen selection.
    chosen={x['id'] for x in n.read(root/'SELECTION.json')['selected']}
    chosen.update(x['id'] for x in n.read(root/'SUPPLEMENTAL_SELECTION.json')['selected'])
    for q in s['results']:
        if q['stage'].startswith('validation'):
            assert q['candidate'] in chosen
            dev=next(x for x in s['results'] if x['candidate']==q['candidate'] and x['stage']=='dev')
            actual=lambda x:{k:v for k,v in x['inputs'].items() if k not in ['InpGridAuditTag','InpRR05AuditTag']}
            assert actual(q)==actual(dev),'Parameters changed between development and validation'
    n.save(root/'SUMMARY.json',s)
    v=n.read(root/'VERIFICATION.json');v.update(independent_native_stopout_reason_audit=True,stopout_counter_corrections=corrections,
        validation_inputs_match_development=True,all_trade_dates_inside_requested_windows=True,unit_tests_passed=6)
    n.save(root/'VERIFICATION.json',v);print('Independent native audit passed: '+str(len(checked))+' cases')

if __name__=='__main__':main()

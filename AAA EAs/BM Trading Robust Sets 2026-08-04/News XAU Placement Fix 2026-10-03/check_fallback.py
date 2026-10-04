"""Isolated native fault-injection check, NOT a performance backtest.

Simulate a crossed buy level, skip the first sell submission, close the buy
as if manually, then discard/reload side masks. Must repair only the missing
sell, recover accepted sides and never buy twice during the same event.
"""
import gzip
import json
import run as study


def main():
    study.free()
    name='New-fault-test'
    source=study.R/'snapshot'/(name+'.mq5')
    body=study.read(study.R/'snapshot/New-fixed-test.mq5').replace('\r\n','\n')
    body=body.replace('int      g_side_required=0;',
        'bool g_fault_skip_sell=true,g_fault_restored=false;\nint      g_side_required=0;',1)
    old='g_event_buy_entry=buy_entry;g_event_sell_entry=sell_entry;'
    assert old in body
    body=body.replace(old,'g_event_buy_entry=tick.ask-SymbolInfoDouble(_Symbol,SYMBOL_POINT);g_event_sell_entry=sell_entry;',1)
    old='if(allow_sell && (g_side_required & 2)!=0) NP_SendSide(false,g_event_sell_entry,side_risk,expiry,prefix+"S");'
    assert old in body
    body=body.replace(old,'''if(allow_sell && (g_side_required & 2)!=0)
   {
      if(g_fault_skip_sell){g_fault_skip_sell=false;Print("FAULT_SKIP_SELL_ONCE");}
      else NP_SendSide(false,g_event_sell_entry,side_risk,expiry,prefix+"S");
   }''',1)
    old='if(!complete)\n   {'
    assert old in body
    body=body.replace(old,'''if(complete && !g_fault_restored)
   {
      g_fault_restored=true;
      NP_ClosePositions(); // Simulate a manual close before the release.
      g_side_accepted=0;g_side_inflight=0;g_side_required=0;
      NP_LoadSideState();NP_ReconcileSides();
      Print("FAULT_RESTORED|accepted=",g_side_accepted,"|required=",g_side_required);
   }
   if(!complete)
   {''',1)
    source.write_text(body)
    study.compile_one(name)
    result=study.run(name,150,'2026.10.02','2026.10.03')
    folder=study.R/'native'/result['tag']
    journal=gzip.decompress((folder/'journal.gz').read_bytes()).decode()
    assert 'FAULT_SKIP_SELL_ONCE' in journal
    assert 'FAULT_RESTORED|accepted=3|required=3' in journal
    assert result['market_fallbacks']>0 and result['incomplete']>0
    assert result['max_same_side_per_event']==1 and result['closure_violations']==0
    assert list(result['audit'][1:3])==['1','1']
    study.save(study.R/'FAULT_CHECK.json',dict(passed=True,not_performance_evidence=True,
        case=result['tag'],tested=['crossed buy market fallback','missing sell repair',
        'accepted-mask reload after manual close','no same-side event re-entry'],
        source_sha=result['source_sha'],binary_sha=result['binary_sha']))
    study.status('PASS native fault-injection check; not performance evidence')


if __name__=='__main__':main()

from run import closing_deals
from analyse import stats

def test_fifo_fragments_are_one_exit_not_two(tmp_path):
    rows=[
      ['2026.07.01 00:00:00','1','XAUUSD','buy','in','0.01','100','1','-0.03','0','0','10000','A'],
      ['2026.07.02 00:00:00','2','XAUUSD','buy','in','0.02','105','2','-0.06','0','0','10000','B'],
      ['2026.07.03 00:00:00','3','XAUUSD','sell','out','0.02','110','3','-0.06','0','10','10010',''],
      ['2026.07.04 00:00:00','4','XAUUSD','sell','out','0.01','101','4','-0.03','0','-4','10006','']]
    p=tmp_path/'report.htm'
    p.write_text('Initial Deposit<b>Deals</b>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>' for row in rows),encoding='utf-16')
    t=closing_deals(p,'test')
    assert len(t)==2
    assert t[0]['exit_deal']=='3' and t[1]['exit_deal']=='4'
    assert abs(t[0]['net_profit']-9.88)<1e-9
    assert abs(sum(x['net_profit'] for x in t)-5.82)<1e-9
    s=stats.trade_statistics(t,'2026.07.01','2026.08.01','XAUUSD')
    assert s['trades']==2 and s['net_win_rate_pct']==50
    assert s['longest_win_streak']==1 and s['longest_loss_streak']==1

def test_empty_ledger_not_a_winner():
    s=stats.trade_statistics([],'2026.07.01','2026.08.01','XAUUSD')
    assert s['trades']==0 and s['net_profit_factor'] is None and s['net_win_rate_pct']==0

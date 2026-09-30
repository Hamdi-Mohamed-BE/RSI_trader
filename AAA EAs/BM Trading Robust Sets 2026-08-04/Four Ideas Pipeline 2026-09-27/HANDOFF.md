# Completed research; do not deploy

2026-09-27: all four screenshot strategies evaluated under the frozen canonical
pipeline. Only USDJPY passed the raw numeric gate. Its staged optimization completed
384 evaluations (339 distinct parameter vectors), three native validations and one
historical holdout. The chosen version failed the holdout at -98.8607% return,
0.19785 net PF, 98.99% native equity DD. No retuning or fallback selection after failure.

Raw failures: US30 filtered Tuesday underperforms its control on frozen return/DD;
US100 daily and NY ORB fail long-window net PF >=1.15. US30 and USTEC overnight
01:05 quote coverage begins only mid-2023 despite the nominal five-year request.

No EA, BAT, website, live account, production settings or Git remote changed.
No live trading API called. Native tasks have finished. Do not restart the entire
queue unnecessarily; results, reports and hashes are retained. No Monte Carlo or
FTMO pass probability is claimed after the failed holdout. Read REPORT.md,
FINAL_CHECKS.json and the two protocols before a follow-up.

Audit amendment: original close-price FX conversion approximation was too strict
for some generated-tick fills. extended_audit.py records those differences with a
2% sanity bound and retains exact report/deal cash reconciliation. No deal or
strategy was edited. The original frozen runner remains unchanged, invoked by
continue_pipeline.py with the amended audit.

Neighbourhood caveat: step-lock does not use trail_distance. Each 27-evaluation
neighbourhood contains nine distinct active range-time/exit-time cases, equally
triplicated. All nine are profitable in development; duplicate outcomes were
checked exactly. This is not 27 independent robustness observations.

The optimization used research Exness leverage 1:2000; its tiny stops require lots
that cannot be carried by a $10K FTMO Swing USDJPY 1:30 account. Do not copy the
rejected vector into a production SET. The first held-out trade needs about $87,733
margin at 1:30; all 446 held-out fills exceed equity-at-placement in this margin
counterfactual. Any later broker-feasible study is a newly frozen hypothesis and
needs fresh validation rather than reuse of this now-exposed holdout.

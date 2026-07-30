# News AI Research

This folder is the standalone home for the news-direction research created in
this Codex task. It contains the trained models, official release text, cached
XAUUSD event-day bid/ask data, validation rows, and reproducible training code.

## What is modeled

- Events: NFP, GDP, CPI, PPI, and FOMC.
- Market: XAUUSD one-minute bid and ask data.
- Pre-release model: price and volume features frozen 30 minutes before release.
- Post-release model: official BLS, BEA, or Federal Reserve text plus pre-release
  market context, with entry one minute after publication.
- Split: 13 years of training followed by a strict two-year validation window.

The post-release text model is not a 30-minute advance prediction. It reads
information that only exists after publication and is evaluated with a delayed
entry. A true pre-release surprise model additionally needs a licensed,
point-in-time archive of analyst forecasts.

## Main artifacts

- `news_direction_model.joblib`: selected pre-release price model.
- `news_official_text_model.joblib`: training-CV-selected official-text model.
- `news_15y_report.json`: pre-release 15-year study report.
- `news_ml_comparison_report.json`: nonlinear pre-release model comparison.
- `news_official_text_hybrid_report.json`: price vs text vs hybrid comparison.
- `news_official_text_hybrid_validation.csv`: selected hybrid validation trades.
- `data/news-event-days/`: cached XAUUSD event-day bid and ask candles.
- `data/official-release-text/`: cached official release documents.

## Run

1. Run `run_collect_official_text.bat` to fill or refresh the official archive.
2. Run `run_train_models.bat` to rebuild both selected models and reports.
3. Run `run_full_research.bat` to do both steps.

The batch files use `uv` and create a local `.venv`. Existing cache files are
reused, so subsequent runs are much faster and avoid unnecessary downloads.

The official-text model is saved for reproducibility, but the current report
marks it research-only because it failed to produce a profitable two-year
validation edge. The existing pre-release model remains the preferred artifact.

## Research safeguards

- Time-series cross-validation only; no random shuffling.
- The final two years are untouched during model selection.
- Bid/ask execution and spread are included.
- Missing one-sided historical quotes are disclosed in each report.
- Results are historical research, not guaranteed live performance.
- Forex Factory content is not copied. Text comes from official public releases.

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from calendar_provider import upcoming_us_events
from news_core import EVENTS, ROOT
from predict_news import load_env, make_prediction


load_env()
app = FastAPI(title="Gold News Impulse Predictor", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    options = "".join(f'<option value="{event}">{event}</option>' for event in EVENTS)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Gold News Impulse Predictor</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter,Segoe UI,sans-serif; background:#070a0f; color:#f5f7fb; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; background:#070a0f; }}
    header {{ border-bottom:1px solid #222a36; padding:18px 24px; display:flex; justify-content:space-between; }}
    main {{ max-width:980px; margin:0 auto; padding:48px 24px; }}
    h1 {{ font-size:34px; margin:0 0 8px; }}
    p {{ color:#9ba7b8; }}
    .panel {{ border:1px solid #283241; border-radius:8px; padding:24px; background:#0c1119; }}
    form {{ display:grid; grid-template-columns:1fr 2fr auto; gap:12px; align-items:end; }}
    label {{ display:grid; gap:8px; color:#a9b5c5; font-size:13px; }}
    select,input,button {{ min-height:44px; border-radius:6px; border:1px solid #344154; padding:0 12px; font:inherit; }}
    select,input {{ background:#080d14; color:#fff; }}
    button {{ background:#25c69a; color:#04110d; border:0; font-weight:700; cursor:pointer; padding:0 20px; }}
    pre {{ margin-top:20px; white-space:pre-wrap; overflow-wrap:anywhere; background:#06090e; border:1px solid #222a36; border-radius:6px; padding:18px; min-height:120px; }}
    .notice {{ margin-top:16px; font-size:13px; }}
    @media(max-width:700px) {{ form {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} }}
  </style>
</head>
<body>
  <header><strong>Gold News AI</strong><span>Prediction only</span></header>
  <main>
    <h1>XAUUSD News Impulse</h1>
    <p>Run a permanently saved prediction 15-30 minutes before a supported USD release.</p>
    <section class="panel">
      <form id="form">
        <label>Event<select name="event">{options}</select></label>
        <label>Release time (UTC)<input name="release" type="datetime-local" required></label>
        <button type="submit">Predict</button>
      </form>
      <pre id="output">Waiting for a query.</pre>
      <p class="notice">No order placement or account management exists in this application.</p>
    </section>
  </main>
  <script>
    document.getElementById('form').addEventListener('submit', async (event) => {{
      event.preventDefault();
      const output = document.getElementById('output');
      output.textContent = 'Running model...';
      const body = new FormData(event.target);
      body.set('release', body.get('release') + ':00Z');
      const response = await fetch('/api/predict', {{method:'POST', body}});
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
    }});
  </script>
</body>
</html>"""


@app.get("/api/health")
def health() -> dict:
    models = {
        lead: (ROOT / "models" / f"gold_news_impulse_{lead}m.joblib").exists()
        for lead in (15, 30)
    }
    return {"status": "ok" if all(models.values()) else "models_missing", "models": models, "trade_execution": False}


@app.get("/api/backtest")
def backtest() -> dict:
    path = ROOT / "backtest_report.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run train_model.bat first.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/upcoming")
def upcoming(days: int = 7) -> dict:
    return upcoming_us_events(max(1, min(days, 30)))


@app.post("/api/predict")
def predict(event: str = Form(...), release: str = Form(...)) -> dict:
    try:
        parsed = datetime.fromisoformat(release.replace("Z", "+00:00")).astimezone(timezone.utc)
        return make_prediction(event, parsed)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

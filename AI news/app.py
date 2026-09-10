from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from ea_file_bridge import (
    file_bridge_status,
    next_event_payload,
    start_file_bridge,
    stop_file_bridge,
)
from news_core import ROOT
from predict_news import load_env, make_prediction
from release_intelligence import analyze_release, build_pre_release_packet
from news_v9_direction import SUPPORTED_EVENTS


load_env()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_file_bridge()
    try:
        yield
    finally:
        stop_file_bridge()


app = FastAPI(
    title="Gold News Impulse Predictor",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    options = "".join(
        f'<option value="{event}">{event}</option>'
        for event in SUPPORTED_EVENTS
    )
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
    form {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; align-items:end; }}
    label {{ display:grid; gap:8px; color:#a9b5c5; font-size:13px; }}
    select,input,button {{ min-height:44px; border-radius:6px; border:1px solid #344154; padding:0 12px; font:inherit; }}
    select,input {{ background:#080d14; color:#fff; }}
    button {{ background:#25c69a; color:#04110d; border:0; font-weight:700; cursor:pointer; padding:0 20px; }}
    pre {{ margin-top:20px; white-space:pre-wrap; overflow-wrap:anywhere; background:#06090e; border:1px solid #222a36; border-radius:6px; padding:18px; min-height:120px; }}
    .notice {{ margin-top:16px; font-size:13px; }}
    .stack {{ display:grid; gap:18px; }}
    .section-title {{ margin:0 0 6px; font-size:19px; }}
    .wide {{ grid-column:1/-1; }}
    .secondary {{ background:#192231; color:#eaf0f8; border:1px solid #344154; }}
    .phase {{ color:#70ddbd; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    @media(max-width:700px) {{ form {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} }}
  </style>
</head>
<body>
  <header><strong>Gold News AI</strong><span>Prediction + MT5 bridge</span></header>
  <main>
    <h1>XAUUSD News Impulse</h1>
    <p>Estimate whether a supported USD release will be positive or negative for gold.</p>
    <section class="stack">
    <div class="panel">
      <div class="phase">Before publication</div>
      <h2 class="section-title">Pre-release forecast</h2>
      <form id="forecast-form">
        <label>Event<select name="event">{options}</select></label>
        <label>Release time (UTC)<input name="release" type="datetime-local" required></label>
        <label>Forecast<input name="forecast" placeholder="optional consensus"></label>
        <label>Previous<input name="previous" placeholder="optional previous value"></label>
        <label class="wide">Official source URL<input name="source_url" placeholder="optional"></label>
        <div class="wide panel" style="padding:16px">
          <div class="phase">FOMC only — optional FedWatch snapshot</div>
          <p style="margin:8px 0 12px">Enter probabilities captured before the release. Leave blank for other events.</p>
          <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">
            <label>Current target lower %<input name="fomc_current_lower" type="number" step="0.001"></label>
            <label>Current target upper %<input name="fomc_current_upper" type="number" step="0.001"></label>
            <label>50bp cut probability %<input name="fomc_cut_50_probability" type="number" min="0" step="0.1"></label>
            <label>25bp cut probability %<input name="fomc_cut_25_probability" type="number" min="0" step="0.1"></label>
            <label>Hold probability %<input name="fomc_hold_probability" type="number" min="0" step="0.1"></label>
            <label>25bp hike probability %<input name="fomc_hike_25_probability" type="number" min="0" step="0.1"></label>
            <label>50bp hike probability %<input name="fomc_hike_50_probability" type="number" min="0" step="0.1"></label>
          </div>
        </div>
        <button class="wide" type="submit">Predict gold impact</button>
      </form>
      <pre id="forecast-output">Waiting for a query.</pre>
    </div>
    <div class="panel">
      <div class="phase">After publication</div>
      <h2 class="section-title">Release interpretation</h2>
      <form id="release-form">
        <label>Event<select name="event">{options}</select></label>
        <label>Release time (UTC)<input name="release_time" type="datetime-local" required></label>
        <label>Actual<input name="actual" placeholder="e.g. 2.4%"></label>
        <label>Forecast<input name="forecast" placeholder="e.g. 2.1%"></label>
        <label>Previous<input name="previous" placeholder="e.g. 2.0%"></label>
        <label>Revised<input name="revised" placeholder="optional"></label>
        <label class="wide">Official source URL<input name="source_url" placeholder="Optional BLS, BEA, or Federal Reserve HTTPS URL"></label>
        <label class="wide">Previous FOMC statement URL<input name="previous_source_url" placeholder="Optional; enables deterministic statement comparison"></label>
        <button class="wide secondary" type="submit">Analyze published release</button>
      </form>
      <pre id="release-output">Waiting for published data.</pre>
    </div>
    <p class="notice">This service computes and publishes signals. The attached MT5 EA owns order placement and risk controls.</p>
    </section>
  </main>
  <script>
    document.getElementById('forecast-form').addEventListener('submit', async (event) => {{
      event.preventDefault();
      const output = document.getElementById('forecast-output');
      output.textContent = 'Running model...';
      const body = new FormData(event.target);
      for (const name of [
        'fomc_current_lower',
        'fomc_current_upper',
        'fomc_cut_50_probability',
        'fomc_cut_25_probability',
        'fomc_hold_probability',
        'fomc_hike_25_probability',
        'fomc_hike_50_probability'
      ]) {{
        if (!body.get(name)) body.delete(name);
      }}
      body.set('release', body.get('release') + ':00Z');
      const response = await fetch('/api/predict', {{method:'POST', body}});
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
    }});
    document.getElementById('release-form').addEventListener('submit', async (event) => {{
      event.preventDefault();
      const output = document.getElementById('release-output');
      output.textContent = 'Analyzing release...';
      const body = new FormData(event.target);
      body.set('release_time', body.get('release_time') + ':00Z');
      const response = await fetch('/api/analyze-release', {{method:'POST', body}});
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
    }});
  </script>
</body>
</html>"""


@app.get("/api/health")
def health() -> dict:
    direction_ready = (ROOT / "models" / "gold_news_v9_direction.joblib").exists()
    magnitude_ready = (ROOT / "models" / "gold_news_v8_move_range.joblib").exists()
    return {
        "status": "ok" if direction_ready and magnitude_ready else "model_missing",
        "models": {
            "gold_direction_v9_action_tier": direction_ready,
            "gold_move_range_v8": magnitude_ready,
        },
        "ea_signal_api": True,
        "server_places_orders": False,
        "mt5_file_bridge": file_bridge_status(),
    }


@app.get("/api/upcoming")
def upcoming(days: int = 7) -> dict:
    payload = upcoming_us_events(max(1, min(days, 30)))
    payload["events"] = [
        event
        for event in payload.get("events", [])
        if event.get("event") in SUPPORTED_EVENTS
    ]
    payload["supported_events"] = list(SUPPORTED_EVENTS)
    return payload


@app.get("/api/ea/next")
def ea_next_event(days: int = 30) -> dict:
    return next_event_payload(days)


@app.post("/api/ea/signal")
def ea_signal(
    event: str = Form(...),
    release: str = Form(...),
    forecast: str | None = Form(None),
    previous: str | None = Form(None),
) -> dict:
    try:
        parsed = datetime.fromisoformat(
            release.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        result = make_prediction(
            event,
            parsed,
            forecast=forecast or None,
            previous=previous or None,
        )
        expected = result.get("expected_impulse_range_usd", {})
        model = result.get("model", {})
        return {
            "status": "OK",
            "generated_at_utc": result["generated_at_utc"],
            "event": result["event"],
            "release_utc": result["release_time_utc"],
            "symbol": result["symbol"],
            "direction": result["gold_impact"],
            "confidence_pct": result["confidence_pct"],
            "confidence_tier": result["confidence_tier"],
            "action_tier": result["action_tier"],
            "active_call_allowed": model.get("active_call_allowed", False),
            "artifact_version": model.get("artifact_version"),
            "expected_min_abs_usd": expected.get("minimum_absolute_move"),
            "expected_median_abs_usd": expected.get("median_absolute_move"),
            "expected_max_abs_usd": expected.get("maximum_absolute_move"),
            "reused_locked_prediction": result.get(
                "reused_locked_prediction", False
            ),
        }
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/predict")
def predict(
    event: str = Form(...),
    release: str = Form(...),
    forecast: str | None = Form(None),
    previous: str | None = Form(None),
    source_url: str | None = Form(None),
    fomc_current_lower: float | None = Form(None),
    fomc_current_upper: float | None = Form(None),
    fomc_cut_25_probability: float | None = Form(None),
    fomc_hold_probability: float | None = Form(None),
    fomc_hike_25_probability: float | None = Form(None),
    fomc_cut_50_probability: float | None = Form(None),
    fomc_hike_50_probability: float | None = Form(None),
) -> dict:
    try:
        parsed = datetime.fromisoformat(release.replace("Z", "+00:00")).astimezone(timezone.utc)
        result = make_prediction(
            event,
            parsed,
            forecast=forecast,
            previous=previous,
            source_url=source_url,
            fomc_current_lower=fomc_current_lower,
            fomc_current_upper=fomc_current_upper,
            fomc_cut_25_probability=fomc_cut_25_probability,
            fomc_hold_probability=fomc_hold_probability,
            fomc_hike_25_probability=fomc_hike_25_probability,
            fomc_cut_50_probability=fomc_cut_50_probability,
            fomc_hike_50_probability=fomc_hike_50_probability,
        )
        result["codex_analyst_packet"] = build_pre_release_packet(
            result,
            forecast=forecast,
            previous=previous,
            source_url=source_url,
        )
        packet_dir = ROOT / "analyst_packets"
        packet_dir.mkdir(exist_ok=True)
        packet_path = packet_dir / os.path.basename(result["saved_to"])
        packet_path.write_text(
            json.dumps(result["codex_analyst_packet"], indent=2),
            encoding="utf-8",
        )
        result["codex_analyst_packet"]["saved_to"] = str(packet_path)
        return result
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/analyze-release")
def analyze_published_release(
    event: str = Form(...),
    release_time: str = Form(...),
    actual: str | None = Form(None),
    forecast: str | None = Form(None),
    previous: str | None = Form(None),
    revised: str | None = Form(None),
    source_url: str | None = Form(None),
    previous_source_url: str | None = Form(None),
) -> dict:
    try:
        return analyze_release(
            event=event,
            release_time=release_time,
            actual=actual,
            forecast=forecast,
            previous=previous,
            revised=revised,
            source_url=source_url or None,
            previous_source_url=previous_source_url or None,
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

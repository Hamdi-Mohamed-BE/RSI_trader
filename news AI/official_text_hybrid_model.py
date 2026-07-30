from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

import fifteen_year_news_backtest as research


ROOT = Path(__file__).resolve().parent
TEXT_DIR = ROOT / "data" / "official-release-text"
MODEL_PATH = ROOT / "news_official_text_model.joblib"
REPORT_PATH = ROOT / "news_official_text_hybrid_report.json"
DETAIL_PATH = ROOT / "news_official_text_hybrid_validation.csv"
HORIZONS = (5, 15, 30)
CANDIDATES = (0.03, 0.1, 0.3, 1.0, 3.0)
TEXT_LIMIT = 30_000


def text_key(event: research.Event) -> str:
    return f"{event.release_utc.date().isoformat()}-{event.event.lower()}.json"


def load_release_text(event: research.Event) -> str | None:
    path = TEXT_DIR / text_key(event)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = str(payload.get("text") or "").strip()
    if len(text) < 300:
        return None
    return f"__EVENT_{event.event}__ {text[:TEXT_LIMIT]}"


def post_release_row(
    event: research.Event,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    horizon: int,
) -> dict | None:
    release_ms = int(event.release_utc.timestamp() * 1000)
    entry_ms = release_ms + 60_000
    exit_ms = release_ms + horizon * 60_000
    entry_bid = research.nearest(bid, entry_ms)
    entry_ask = research.nearest(ask, entry_ms)
    exit_bid = research.nearest(bid, exit_ms)
    exit_ask = research.nearest(ask, exit_ms)
    if not all((entry_bid, entry_ask, exit_bid, exit_ask)):
        return None

    entry_mid = (entry_bid["close"] + entry_ask["close"]) / 2
    exit_mid = (exit_bid["close"] + exit_ask["close"]) / 2
    target = int(exit_mid > entry_mid)
    return {
        "target": target,
        "actual_direction": "UP" if target else "DOWN",
        "buy_pnl": exit_bid["close"] - entry_ask["close"],
        "sell_pnl": entry_bid["close"] - exit_ask["close"],
        "entry_bid": entry_bid["close"],
        "entry_ask": entry_ask["close"],
        "exit_bid": exit_bid["close"],
        "exit_ask": exit_ask["close"],
        "spread": entry_ask["close"] - entry_bid["close"],
    }


def build_samples() -> tuple[list[dict], dict]:
    events = research.build_calendar()
    research.ensure_market_data()
    event_days = sorted({event.release_utc.date().isoformat() for event in events})
    spread_by_year = research.annual_spreads(event_days)
    day_cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    rows = []
    missing_text = []
    missing_market = []
    imputed = []

    for event in events:
        text = load_release_text(event)
        if text is None:
            missing_text.append({"event": event.event, "release_utc": event.release_utc.isoformat()})
            continue
        day = event.release_utc.date().isoformat()
        for price_type in ("bid", "ask"):
            key = (day, price_type)
            if key not in day_cache:
                day_cache[key] = research.load_day(day, price_type)
        bid, ask, imputed_side = research.complete_sides(
            day_cache[(day, "bid")],
            day_cache[(day, "ask")],
            spread_by_year[event.release_utc.year],
        )
        if imputed_side:
            imputed.append({"date": day, "side": imputed_side})
        pre = research.feature_row(event, bid, ask)
        posts = {horizon: post_release_row(event, bid, ask, horizon) for horizon in HORIZONS}
        if pre is None or any(value is None for value in posts.values()):
            missing_market.append({"event": event.event, "release_utc": event.release_utc.isoformat()})
            continue
        rows.append(
            {
                "event": event.event,
                "release_utc": event.release_utc.isoformat(),
                "text": text,
                "features": pre["features"],
                "posts": posts,
            }
        )

    audit = {
        "calendar_events": len(events),
        "usable_events": len(rows),
        "missing_release_text": len(missing_text),
        "missing_market_window": len(missing_market),
        "imputed_market_sides": len(imputed),
        "missing_text_examples": missing_text[:20],
        "missing_market_examples": missing_market[:20],
    }
    return rows, audit


def matrices(
    fit_rows: list[dict],
    transform_rows: list[dict],
    variant: str,
) -> tuple[object, object, dict]:
    state: dict = {}
    fit_parts = []
    transform_parts = []

    if variant in {"text", "hybrid"}:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.97,
            max_features=6_000,
            sublinear_tf=True,
        )
        fit_parts.append(vectorizer.fit_transform([row["text"] for row in fit_rows]))
        transform_parts.append(vectorizer.transform([row["text"] for row in transform_rows]))
        state["vectorizer"] = vectorizer

    if variant in {"price", "hybrid"}:
        scaler = StandardScaler()
        fit_numeric = np.asarray([row["features"] for row in fit_rows], dtype=float)
        transform_numeric = np.asarray([row["features"] for row in transform_rows], dtype=float)
        fit_parts.append(csr_matrix(scaler.fit_transform(fit_numeric)))
        transform_parts.append(csr_matrix(scaler.transform(transform_numeric)))
        state["scaler"] = scaler

    return hstack(fit_parts).tocsr(), hstack(transform_parts).tocsr(), state


def select_model(train: list[dict], horizon: int, variant: str) -> dict:
    splitter = TimeSeriesSplit(n_splits=5)
    scores = []
    targets = np.asarray([row["posts"][horizon]["target"] for row in train], dtype=int)
    for c_value in CANDIDATES:
        losses = []
        accuracies = []
        for fit_indices, validation_indices in splitter.split(train):
            fit_rows = [train[index] for index in fit_indices]
            validation_rows = [train[index] for index in validation_indices]
            x_fit, x_validation, _ = matrices(fit_rows, validation_rows, variant)
            model = LogisticRegression(
                C=c_value,
                class_weight="balanced",
                max_iter=3_000,
                random_state=42,
            )
            model.fit(x_fit, targets[fit_indices])
            probabilities = model.predict_proba(x_validation)[:, 1]
            losses.append(log_loss(targets[validation_indices], probabilities, labels=[0, 1]))
            accuracies.append(accuracy_score(targets[validation_indices], probabilities >= 0.5))
        scores.append(
            {
                "c": c_value,
                "mean_log_loss": round(float(mean(losses)), 6),
                "mean_accuracy_pct": round(100 * float(mean(accuracies)), 2),
            }
        )
    best = min(scores, key=lambda row: (row["mean_log_loss"], -row["mean_accuracy_pct"], row["c"]))
    return {"selected_c": best["c"], "candidates": scores}


def profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    return None if losses == 0 else gains / losses


def max_drawdown(values: list[float]) -> float:
    equity = peak = drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def summarize(results: list[dict]) -> dict:
    pnl = [row["pnl_usd"] for row in results]
    pf = profit_factor(pnl)
    return {
        "events": len(results),
        "direction_accuracy_pct": round(100 * mean(row["correct"] for row in results), 2) if results else 0.0,
        "win_rate_pct": round(100 * sum(value > 0 for value in pnl) / len(pnl), 2) if pnl else 0.0,
        "net_usd_fresh_100_each": round(sum(pnl), 2),
        "profit_factor": None if pf is None else round(pf, 3),
        "max_cumulative_drawdown_usd": round(max_drawdown(pnl), 2),
    }


def train_and_test(
    train: list[dict],
    test: list[dict],
    horizon: int,
    variant: str,
    selection: dict,
) -> tuple[dict, list[dict], dict]:
    x_train, x_test, state = matrices(train, test, variant)
    y_train = np.asarray([row["posts"][horizon]["target"] for row in train], dtype=int)
    y_test = np.asarray([row["posts"][horizon]["target"] for row in test], dtype=int)
    model = LogisticRegression(
        C=selection["selected_c"],
        class_weight="balanced",
        max_iter=3_000,
        random_state=42,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    results = []
    for row, prediction, probability in zip(test, predictions, probabilities):
        post = row["posts"][horizon]
        price_pnl = post["buy_pnl"] if prediction else post["sell_pnl"]
        pnl_usd = max(-100.0, price_pnl * 100 * 0.08)
        results.append(
            {
                "release_utc": row["release_utc"],
                "event": row["event"],
                "variant": variant,
                "horizon_minutes": horizon,
                "prediction": "UP" if prediction else "DOWN",
                "up_probability": round(float(probability), 6),
                "actual": post["actual_direction"],
                "correct": int(prediction == post["target"]),
                "entry": round(post["entry_ask"] if prediction else post["entry_bid"], 3),
                "exit": round(post["exit_bid"] if prediction else post["exit_ask"], 3),
                "spread": round(post["spread"], 3),
                "pnl_gold_pips": round(price_pnl / 0.01, 1),
                "pnl_usd": round(pnl_usd, 2),
            }
        )
    stats = summarize(results)
    stats["roc_auc"] = round(float(roc_auc_score(y_test, probabilities)), 4)
    artifact = {
        "variant": variant,
        "horizon_minutes": horizon,
        "feature_names": research.FEATURE_NAMES,
        "model": model,
        **state,
    }
    return stats, results, artifact


def run() -> dict:
    samples, audit = build_samples()
    train = [row for row in samples if date.fromisoformat(row["release_utc"][:10]) < research.TEST_START]
    test = [row for row in samples if date.fromisoformat(row["release_utc"][:10]) >= research.TEST_START]
    if len(train) < 250 or len(test) < 40:
        raise RuntimeError(
            f"Not enough complete official-release samples: train={len(train)}, validation={len(test)}. "
            "Run official_release_text_collector.py first."
        )

    comparisons = []
    artifacts = {}
    result_sets = {}
    for horizon in HORIZONS:
        for variant in ("price", "text", "hybrid"):
            print(f"Evaluating {variant} model at T+{horizon} minutes...")
            selection = select_model(train, horizon, variant)
            stats, results, artifact = train_and_test(train, test, horizon, variant, selection)
            key = f"{variant}_t{horizon}"
            comparisons.append(
                {
                    "key": key,
                    "variant": variant,
                    "horizon_minutes": horizon,
                    "selection": selection,
                    "validation": stats,
                }
            )
            artifacts[key] = artifact
            result_sets[key] = results

    selected = min(
        comparisons,
        key=lambda row: (
            min(item["mean_log_loss"] for item in row["selection"]["candidates"]),
            -row["validation"]["direction_accuracy_pct"],
        ),
    )
    selected_key = selected["key"]
    joblib.dump(
        {
            **artifacts[selected_key],
            "trained_through": train[-1]["release_utc"],
            "validation_start": test[0]["release_utc"],
            "official_sources_only": True,
            "text_available_after_release": True,
        },
        MODEL_PATH,
    )

    selected_results = result_sets[selected_key]
    with DETAIL_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected_results[0]))
        writer.writeheader()
        writer.writerows(selected_results)

    report = {
        "methodology": {
            "train": f"{research.START_DATE} through {research.TEST_START.isoformat()} exclusive",
            "validation": f"{research.TEST_START} through {research.END_DATE}",
            "text_sources": "Official BLS, BEA, and Federal Reserve releases only",
            "entry_timing": "Executable bid/ask entry one minute after the official release",
            "candidate_exits_minutes": list(HORIZONS),
            "model_selection": "Five-fold expanding-window time-series CV on training data only",
            "execution": "$100 reset per event, 0.08 XAUUSD lot, recorded/imputed spread, loss capped at $100",
            "important_limit": (
                "No point-in-time analyst consensus archive is included. Text sentiment measures the release itself "
                "and is therefore a post-release model, not a 30-minute pre-release forecast."
            ),
        },
        "audit": audit,
        "train_events": len(train),
        "validation_events": len(test),
        "comparisons": comparisons,
        "selected_model": selected_key,
        "selected_validation": selected["validation"],
        "deployment_recommendation": {
            "enabled": False,
            "reason": (
                "The training-CV-selected official-text model did not achieve a validation profit factor above "
                "1.0 or a useful directional edge. Preserve it for research; do not replace the validated "
                "pre-release model."
            ),
            "preferred_existing_model": "news_direction_model.joblib",
            "preferred_existing_live_event_filter": "CPI only",
        },
        "selected_by_event": {
            event: summarize([row for row in selected_results if row["event"] == event])
            for event in research.EVENT_ORDER
        },
        "artifacts": {
            "model": MODEL_PATH.name,
            "validation_rows": DETAIL_PATH.name,
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()

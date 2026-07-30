from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import fifteen_year_news_backtest as research


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "data" / "official-release-text"
MANIFEST_PATH = ROOT / "official_release_text_manifest.json"
USER_AGENT = "Mozilla/5.0 (compatible; XAU-event-research/1.0; contact=research@example.com)"
PRINT_LOCK = Lock()


def request_text(url: str) -> str:
    error = None
    for attempt in range(5):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            error = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Failed to download {url}") from error


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script,style,nav,header,footer,form,aside"):
        tag.decompose()
    main = (
        soup.select_one("main")
        or soup.select_one("#content")
        or soup.select_one(".field--name-body")
        or soup.body
        or soup
    )
    text = main.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def bea_urls() -> dict[str, str]:
    mapping = {}
    for page in range(18):
        url = (
            "https://www.bea.gov/news/archive"
            f"?field_related_product_target_id=451&created_1=All&title=&page={page}"
        )
        soup = BeautifulSoup(request_text(url), "html.parser")
        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            link = row.find("a", href=True)
            if len(cells) < 2 or not link:
                continue
            title = cells[0].get_text(" ", strip=True).lower()
            if "advance estimate" not in title and "initial estimate" not in title:
                continue
            try:
                released = datetime.strptime(cells[1].get_text(" ", strip=True), "%B %d, %Y")
            except ValueError:
                continue
            mapping[released.date().isoformat()] = urljoin("https://www.bea.gov", link["href"])
    return mapping


def event_url(event: research.Event, gdp_mapping: dict[str, str]) -> str | None:
    day = event.release_utc.date()
    if event.event in {"NFP", "CPI", "PPI"}:
        slug = {"NFP": "empsit", "CPI": "cpi", "PPI": "ppi"}[event.event]
        return f"https://www.bls.gov/news.release/archives/{slug}_{day.strftime('%m%d%Y')}.htm"
    if event.event == "FOMC":
        return (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            f"monetary{day.strftime('%Y%m%d')}a.htm"
        )
    if event.event == "GDP":
        return gdp_mapping.get(day.isoformat())
    return None


def collect_one(event: research.Event, url: str) -> dict:
    key = f"{event.release_utc.date().isoformat()}-{event.event.lower()}"
    path = CACHE_DIR / f"{key}.json"
    if path.exists() and path.stat().st_size > 300:
        return json.loads(path.read_text(encoding="utf-8"))
    text = clean_html(request_text(url))
    if len(text) < 300:
        raise RuntimeError(f"Release text is unexpectedly short: {url}")
    payload = {
        "event": event.event,
        "release_utc": event.release_utc.isoformat(),
        "url": url,
        "text": text,
        "characters": len(text),
    }
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return payload


def run() -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    events = research.build_calendar()
    gdp_mapping = bea_urls()
    work = [(event, event_url(event, gdp_mapping)) for event in events]
    work = [(event, url) for event, url in work if url]
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(collect_one, event, url): (event, url) for event, url in work}
        for index, future in enumerate(as_completed(futures), start=1):
            event, url = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                failures.append(
                    {
                        "event": event.event,
                        "release_utc": event.release_utc.isoformat(),
                        "url": url,
                        "error": str(error),
                    }
                )
            if index % 50 == 0:
                with PRINT_LOCK:
                    print(f"Release text: {index}/{len(work)} complete, failures={len(failures)}")
    results.sort(key=lambda item: item["release_utc"])
    manifest = {
        "requested": len(events),
        "with_url": len(work),
        "collected": len(results),
        "failures": failures,
        "items": [
            {
                "event": item["event"],
                "release_utc": item["release_utc"],
                "url": item["url"],
                "characters": item["characters"],
            }
            for item in results
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("requested", "with_url", "collected")}, indent=2))
    print(f"Failures: {len(failures)}")
    return results


if __name__ == "__main__":
    run()

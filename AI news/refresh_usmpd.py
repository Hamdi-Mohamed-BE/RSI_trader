from __future__ import annotations

import io
import zipfile
from pathlib import Path

import requests

from news_core import ROOT


USMPD_XLSX_URL = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
SURPRISES_ZIP_URL = (
    "https://www.frbsf.org/wp-content/uploads/"
    "monetary-policy-surprises.zip"
)
DATA_DIR = ROOT / "data"
SURPRISES_DIR = DATA_DIR / "monetary-policy-surprises"


def _download(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def refresh() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    workbook = _download(USMPD_XLSX_URL)
    archive = _download(SURPRISES_ZIP_URL)
    (DATA_DIR / "USMPD.xlsx").write_bytes(workbook)

    SURPRISES_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        safe_members = [
            member
            for member in bundle.infolist()
            if not member.is_dir()
            and Path(member.filename).name == member.filename
        ]
        for member in safe_members:
            (SURPRISES_DIR / member.filename).write_bytes(
                bundle.read(member)
            )

    with (SURPRISES_DIR / "mps.csv").open(encoding="utf-8") as handle:
        surprise_rows = sum(1 for _ in handle) - 1
    return {
        "source": (
            "Federal Reserve Bank of San Francisco U.S. Monetary Policy "
            "Event-Study Database"
        ),
        "workbook_bytes": len(workbook),
        "archive_bytes": len(archive),
        "surprise_rows": surprise_rows,
    }


if __name__ == "__main__":
    print(refresh())

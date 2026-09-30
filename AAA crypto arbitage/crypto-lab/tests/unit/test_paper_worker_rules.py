from datetime import timedelta
from decimal import Decimal

from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.workers.cex import quote
from crypto_lab.workers.copy import resolved_price
from crypto_lab.workers.solana import eligible

D = Decimal


def test_depth_not_just_top_price():
    levels = [["10", "1"], ["12", "2"]]
    assert quote(levels, D(2)) == 22
    assert quote(levels, D(4)) is None


def test_resolution_requires_final_status_and_matching_token():
    row = {
        "closed": True,
        "umaResolutionStatus": "resolved",
        "clobTokenIds": '["a", "b"]',
        "outcomePrices": '["0", "1"]',
    }
    assert resolved_price(row, "a") == 0
    assert resolved_price(row, "b") == 1
    assert resolved_price(row, "c") is None
    assert resolved_price({**row, "umaResolutionStatus": "proposed"}, "b") is None
    assert resolved_price({**row, "outcomePrices": '["0.01", "0.99"]'}, "b") is None


def test_token_filters_fail_closed_when_risk_metadata_missing():
    token = {
        "isVerified": True,
        "tags": ["meme"],
        "liquidity": 300000,
        "audit": {"mintAuthorityDisabled": True, "freezeAuthorityDisabled": True, "topHoldersPercentage": 20},
        "firstPool": {"createdAt": (utcnow() - timedelta(days=30)).isoformat()},
        "updatedAt": utcnow().isoformat(),
    }
    assert eligible(token)
    assert not eligible({**token, "audit": {}})
    assert not eligible({**token, "liquidity": 100})
    assert not eligible({**token, "updatedAt": (utcnow() - timedelta(hours=1)).isoformat()})

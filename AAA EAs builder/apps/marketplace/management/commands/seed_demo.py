from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.marketplace.models import Product, TestRun

EQUITY_POINTS = [
    10000,
    9920,
    10140,
    10080,
    10320,
    10270,
    10610,
    10980,
    11120,
    11040,
    11460,
    11320,
    11780,
    12140,
    12020,
    12490,
    12820,
    12660,
    13180,
    13540,
    13320,
    13890,
    14210,
    14080,
    14560,
    14720,
]

DRAWDOWN_POINTS = [
    0,
    -0.8,
    -0.2,
    -1.1,
    -0.4,
    -1.6,
    -0.5,
    -0.1,
    -1.0,
    -2.4,
    -0.4,
    -1.5,
    -0.3,
    -0.2,
    -1.9,
    -0.4,
    -0.1,
    -2.8,
    -0.6,
    -0.2,
    -1.7,
    -0.3,
    -2.1,
    -0.4,
    -0.1,
    -0.2,
]


class Command(BaseCommand):
    help = "Create safe fictional marketplace content for local development."

    def handle(self, *args, **options):
        product, _ = Product.objects.update_or_create(
            slug="apex-pulse-ea",
            defaults={
                "name": "Apex Pulse EA",
                "summary": "A volatility-aware EURUSD trend system with explicit risk controls.",
                "description": (
                    "A fictional demonstration product for the marketplace interface. It combines "
                    "trend confirmation with volatility-adjusted entries and position sizing."
                ),
                "artifact_type": Product.ArtifactType.MT5_EA,
                "status": Product.Status.PUBLISHED,
                "price": Decimal("149.00"),
                "currency": "USD",
                "current_version": "2.4.1",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "strategy_type": "Trend following",
                "source_included": True,
                "support_days": 30,
                "tags": ["trend", "volatility", "risk-managed"],
            },
        )
        TestRun.objects.update_or_create(
            product=product,
            defaults={
                "verification": TestRun.Verification.PLATFORM_PARSED,
                "is_demo": True,
                "start_date": date(2021, 1, 1),
                "end_date": date(2025, 12, 31),
                "initial_deposit": Decimal("10000.00"),
                "leverage": "1:100",
                "modelling": "Every tick based on real ticks",
                "commission_included": True,
                "profit_factor": Decimal("1.74"),
                "win_rate": Decimal("62.80"),
                "max_drawdown": Decimal("8.40"),
                "total_trades": 486,
                "net_return": Decimal("47.20"),
                "equity_points": EQUITY_POINTS,
                "drawdown_points": DRAWDOWN_POINTS,
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo marketplace data is ready."))

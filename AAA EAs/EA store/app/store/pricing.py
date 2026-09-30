"""Store prices: 40% below the catalogue list price, plus the buy-3-get-1-free pack rule.

The catalogue (``app/catalog.py``) keeps its list prices unchanged; this module
is the single place that turns them into what the store displays and charges.
All arithmetic is in integer US cents to avoid float rounding.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol

DISCOUNT_RATE = Decimal("0.40")  # every bot is 40% below today's catalogue price
PACK_SIZE = 4  # for every 4 bots in a cart, the cheapest one is free
PACKAGE_LIST_PRICE = 1990  # "Complete Available Portfolio" list price (USD)
BUY3_PACKAGE_LIST_PRICE = 499  # legacy "Choose 3 + bonus" list price, shown for reference

PACK_RULE_TEXT = (
    "Buy 3, get 1 free: for every 4 bots in your cart, the cheapest bot is free "
    "(4 bots = 1 free, 8 bots = the 2 cheapest free, and so on)."
)


class PricedProduct(Protocol):
    slug: str
    label: str
    price: int


def discounted_cents(list_price_usd: int | float | Decimal) -> int:
    cents = Decimal(str(list_price_usd)) * 100 * (1 - DISCOUNT_RATE)
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def sale_cents(product: PricedProduct) -> int:
    return discounted_cents(product.price)


def sale_price(product: PricedProduct) -> float:
    return sale_cents(product) / 100


def package_sale_cents() -> int:
    return discounted_cents(PACKAGE_LIST_PRICE)


def cents_to_usd(cents: int) -> float:
    return cents / 100


def format_usd(cents: int) -> str:
    value = cents / 100
    return f"${value:,.0f}" if cents % 100 == 0 else f"${value:,.2f}"


@dataclass
class QuoteLine:
    slug: str
    label: str
    list_cents: int
    sale_cents: int
    charged_cents: int
    free: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "label": self.label,
            "list_cents": self.list_cents,
            "sale_cents": self.sale_cents,
            "charged_cents": self.charged_cents,
            "free": self.free,
        }


@dataclass
class Quote:
    lines: list[QuoteLine] = field(default_factory=list)
    list_total_cents: int = 0  # sum of catalogue list prices
    sale_total_cents: int = 0  # after the 40% reduction, before the pack rule
    pack_discount_cents: int = 0  # value of the free bots
    package_applied: bool = False
    package_discount_cents: int = 0
    total_cents: int = 0
    free_count: int = 0
    rule_text: str = PACK_RULE_TEXT

    @property
    def count(self) -> int:
        return len(self.lines)

    @property
    def discount_cents(self) -> int:
        """Everything below the 40%-reduced subtotal (free bots and package price)."""
        return self.sale_total_cents - self.total_cents

    @property
    def next_free_in(self) -> int:
        return PACK_SIZE - (self.count % PACK_SIZE) if self.count else PACK_SIZE

    def as_dict(self) -> dict[str, Any]:
        return {
            "lines": [line.as_dict() for line in self.lines],
            "list_total_cents": self.list_total_cents,
            "sale_total_cents": self.sale_total_cents,
            "pack_discount_cents": self.pack_discount_cents,
            "package_applied": self.package_applied,
            "package_discount_cents": self.package_discount_cents,
            "total_cents": self.total_cents,
            "free_count": self.free_count,
            "discount_rate": str(DISCOUNT_RATE),
            "pack_size": PACK_SIZE,
            "rule_text": self.rule_text,
        }


def dedupe(slugs: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for slug in slugs:
        if slug not in seen:
            seen.add(slug)
            ordered.append(slug)
    return ordered


def quote(products: Sequence[PricedProduct], all_sellable_slugs: Iterable[str] | None = None) -> Quote:
    """Price a cart of distinct products.

    * each bot: list price − 40%;
    * pack rule: floor(n / 4) bots are free, always the cheapest ones;
    * if the cart holds every sellable bot, the complete-portfolio package price
      applies when it is lower than the pack-rule total.
    """
    unique: dict[str, PricedProduct] = {}
    for product in products:
        unique.setdefault(product.slug, product)
    items = list(unique.values())
    lines = [
        QuoteLine(product.slug, product.label, int(product.price) * 100, sale_cents(product), sale_cents(product))
        for product in items
    ]
    free_count = len(lines) // PACK_SIZE
    # cheapest first; ties broken by label so the result is deterministic
    for line in sorted(lines, key=lambda line: (line.sale_cents, line.label))[:free_count]:
        line.free = True
        line.charged_cents = 0
    result = Quote(lines=lines, free_count=free_count)
    result.list_total_cents = sum(line.list_cents for line in lines)
    result.sale_total_cents = sum(line.sale_cents for line in lines)
    result.pack_discount_cents = sum(line.sale_cents for line in lines if line.free)
    result.total_cents = result.sale_total_cents - result.pack_discount_cents
    if all_sellable_slugs is not None:
        everything = set(all_sellable_slugs)
        if everything and everything == set(unique) and package_sale_cents() < result.total_cents:
            result.package_applied = True
            result.package_discount_cents = result.total_cents - package_sale_cents()
            result.total_cents = package_sale_cents()
            _spread_package_price(lines, result.total_cents)
    return result


def _spread_package_price(lines: list[QuoteLine], total: int) -> None:
    """Allocate the package total over paid lines proportionally (for the order record)."""
    paid = [line for line in lines if not line.free]
    base = sum(line.sale_cents for line in paid)
    if not paid or base <= 0:
        return
    remaining = total
    for index, line in enumerate(paid):
        share = remaining if index == len(paid) - 1 else (line.sale_cents * total) // base
        line.charged_cents = share
        remaining -= share

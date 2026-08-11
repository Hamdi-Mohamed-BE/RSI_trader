from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Product.Status.PUBLISHED).select_related("test_run")


class Product(TimeStampedModel):
    class ArtifactType(models.TextChoices):
        MT5_EA = "mt5_ea", "MT5 Expert Advisor"
        MT5_INDICATOR = "mt5_indicator", "MT5 Indicator"
        PINE_STRATEGY = "pine_strategy", "Pine Strategy"
        PINE_INDICATOR = "pine_indicator", "Pine Indicator"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "In review"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="marketplace_products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=240)
    description = models.TextField()
    artifact_type = models.CharField(max_length=32, choices=ArtifactType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    current_version = models.CharField(max_length=32, default="1.0.0")
    symbol = models.CharField(max_length=32, blank=True)
    timeframe = models.CharField(max_length=16, blank=True)
    strategy_type = models.CharField(max_length=80, blank=True)
    source_included = models.BooleanField(default=True)
    support_days = models.PositiveSmallIntegerField(default=30)
    tags = models.JSONField(default=list, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("status", "artifact_type", "price"))]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("marketplace:detail", kwargs={"slug": self.slug})

    @property
    def performance(self):
        try:
            return self.test_run
        except TestRun.DoesNotExist:
            return None


class TestRun(TimeStampedModel):
    class Verification(models.TextChoices):
        SELLER_REPORTED = "seller_reported", "Seller-reported"
        PLATFORM_PARSED = "platform_parsed", "Platform-parsed report"
        PLATFORM_BACKTESTED = "platform_backtested", "Platform-backtested"
        INDEPENDENT = "independent", "Independently verified"

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="test_run")
    verification = models.CharField(max_length=32, choices=Verification.choices)
    is_demo = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_deposit = models.DecimalField(max_digits=12, decimal_places=2)
    leverage = models.CharField(max_length=20, default="1:100")
    modelling = models.CharField(max_length=120)
    commission_included = models.BooleanField(default=True)
    profit_factor = models.DecimalField(max_digits=8, decimal_places=2)
    win_rate = models.DecimalField(max_digits=6, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=6, decimal_places=2)
    total_trades = models.PositiveIntegerField()
    net_return = models.DecimalField(max_digits=8, decimal_places=2)
    equity_points = models.JSONField(default=list, blank=True)
    drawdown_points = models.JSONField(default=list, blank=True)
    report_checksum = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-end_date",)

    def __str__(self) -> str:
        return f"{self.product.name} · {self.get_verification_display()}"

    @property
    def period_label(self) -> str:
        return f"{self.start_date:%Y}–{self.end_date:%Y}"

    @property
    def ending_balance(self) -> Decimal:
        return self.initial_deposit * (Decimal("1") + self.net_return / Decimal("100"))

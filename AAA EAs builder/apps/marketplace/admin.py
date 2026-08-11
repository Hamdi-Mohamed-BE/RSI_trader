from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Product, TestRun


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        "name",
        "artifact_type",
        "status",
        "price",
        "currency",
        "current_version",
        "updated_at",
    )
    list_filter = ("status", "artifact_type", "source_included")
    search_fields = ("name", "slug", "summary", "description", "symbol", "strategy_type")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("seller",)


@admin.register(TestRun)
class TestRunAdmin(ModelAdmin):
    list_display = (
        "product",
        "verification",
        "is_demo",
        "period_label",
        "profit_factor",
        "max_drawdown",
        "total_trades",
    )
    list_filter = ("verification", "is_demo", "commission_included")
    search_fields = ("product__name", "modelling", "report_checksum")
    autocomplete_fields = ("product",)

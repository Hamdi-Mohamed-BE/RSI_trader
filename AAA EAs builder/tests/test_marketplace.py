import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.marketplace.models import Product


@pytest.mark.django_db
def test_marketplace_lists_published_demo_product(client):
    call_command("seed_demo", verbosity=0)
    response = client.get(reverse("marketplace:list"))
    assert response.status_code == 200
    assert b"Apex Pulse EA" in response.content
    assert b"Demo data" in response.content


@pytest.mark.django_db
def test_marketplace_hides_draft_product(client):
    Product.objects.create(
        name="Draft EA",
        slug="draft-ea",
        summary="Not ready",
        description="Draft",
        artifact_type=Product.ArtifactType.MT5_EA,
        price="10.00",
    )
    response = client.get(reverse("marketplace:list"))
    assert b"Draft EA" not in response.content


@pytest.mark.django_db
def test_product_detail_shows_evidence_context(client):
    call_command("seed_demo", verbosity=0)
    response = client.get(reverse("marketplace:detail", kwargs={"slug": "apex-pulse-ea"}))
    assert response.status_code == 200
    assert b"Hypothetical results" in response.content
    assert b"Max drawdown" in response.content
    assert b"486" in response.content

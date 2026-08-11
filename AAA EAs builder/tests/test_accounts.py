import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_user_can_sign_up_with_email(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "email": "trader@example.com",
            "display_name": "Test Trader",
            "password1": "A-strong-test-password-392!",
            "password2": "A-strong-test-password-392!",
        },
    )
    assert response.status_code == 302
    user = get_user_model().objects.get(email="trader@example.com")
    assert user.display_name == "Test Trader"


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("accounts:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url

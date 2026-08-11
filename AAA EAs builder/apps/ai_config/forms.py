from django import forms

from .models import Gateway


class GatewayAdminForm(forms.ModelForm):
    base_url = forms.URLField(required=False, assume_scheme="https")
    api_key = forms.CharField(
        label="Replace API key",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False),
        help_text="Write-only. Leave blank to keep the current encrypted credential.",
    )

    class Meta:
        model = Gateway
        fields = (
            "name",
            "key",
            "provider",
            "base_url",
            "enabled",
            "priority",
            "timeout_seconds",
            "max_concurrency",
            "daily_budget_usd",
            "extra_config",
            "api_key",
            "notes",
        )

    def save(self, commit=True):
        gateway = super().save(commit=False)
        if api_key := self.cleaned_data.get("api_key"):
            gateway.set_api_key(api_key)
        if commit:
            gateway.save()
            self.save_m2m()
        return gateway

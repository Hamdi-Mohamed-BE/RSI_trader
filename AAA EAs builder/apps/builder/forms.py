from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Project


class ProjectForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "artifact_type", "symbol", "timeframe", "description")
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": (
                        "Example: Trade EURUSD on H1 when EMA 50 crosses EMA 200. "
                        "Risk 1% per trade, use ATR stop loss, and trail after 1R."
                    ),
                }
            )
        }

    def clean_symbol(self) -> str:
        return self.cleaned_data["symbol"].strip().upper()

    def clean_timeframe(self) -> str:
        return self.cleaned_data["timeframe"].strip().upper()


class GenerationRequestForm(TailwindFormMixin, forms.Form):
    prompt = forms.CharField(
        label="Generation instructions",
        max_length=20_000,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": (
                    "Describe any final details or revision instructions. The saved project brief "
                    "is included automatically."
                ),
            }
        ),
        help_text="Be explicit about entries, exits, risk, sessions, and position limits.",
    )
    acknowledge_testing = forms.BooleanField(
        label=(
            "I understand that generated trading code must be reviewed, compiled, and tested on "
            "a demo account before any live use."
        )
    )

    def clean_prompt(self) -> str:
        prompt = self.cleaned_data["prompt"].strip()
        if len(prompt) < 20:
            raise forms.ValidationError("Add at least 20 characters of generation instructions.")
        return prompt


class GenerationChatForm(TailwindFormMixin, forms.Form):
    message = forms.CharField(
        label="Message the generation copilot",
        max_length=8_000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Ask about the current code, diagnostics, progress, or request a complete fix…"
                ),
            }
        ),
    )

    def clean_message(self) -> str:
        message = self.cleaned_data["message"].strip()
        if len(message) < 2:
            raise forms.ValidationError("Enter a question or revision request.")
        return message

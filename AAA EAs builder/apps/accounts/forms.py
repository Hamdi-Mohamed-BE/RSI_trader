from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.core.forms import TailwindFormMixin

from .models import User


class LoginForm(TailwindFormMixin, AuthenticationForm):
    pass


class SignUpForm(TailwindFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")

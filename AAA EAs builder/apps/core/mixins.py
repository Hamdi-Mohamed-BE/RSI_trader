from django.contrib.auth.mixins import LoginRequiredMixin


class OwnedQuerySetMixin(LoginRequiredMixin):
    """Restrict object-based views to records owned by the signed-in user."""

    owner_field = "owner"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_field: self.request.user})


class OwnerFormMixin(LoginRequiredMixin):
    """Assign the signed-in user to new owner-scoped records."""

    owner_field = "owner"

    def form_valid(self, form):
        setattr(form.instance, self.owner_field, self.request.user)
        return super().form_valid(form)

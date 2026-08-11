from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        from apps.marketplace.models import Product

        context = super().get_context_data(**kwargs)
        context["featured_products"] = Product.objects.published()[:3]
        context["demo_equity"] = [
            10000,
            10150,
            10080,
            10420,
            10610,
            10530,
            10980,
            11220,
            11110,
            11640,
            11920,
            11760,
            12380,
            12810,
            12640,
            13220,
            13680,
            13420,
            14150,
            14560,
        ]
        return context


class HealthCheckView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok", "service": "aaa-eas-builder"})

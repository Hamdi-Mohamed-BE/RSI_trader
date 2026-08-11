from django.db.models import Q
from django.views.generic import DetailView, ListView

from .models import Product


class ProductListView(ListView):
    model = Product
    template_name = "marketplace/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.published()
        if query := self.request.GET.get("q", "").strip():
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(summary__icontains=query)
                | Q(symbol__icontains=query)
                | Q(strategy_type__icontains=query)
            )
        if artifact_type := self.request.GET.get("type", "").strip():
            queryset = queryset.filter(artifact_type=artifact_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["artifact_types"] = Product.ArtifactType.choices
        context["query"] = self.request.GET.get("q", "")
        context["selected_type"] = self.request.GET.get("type", "")
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "marketplace/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.published()

from django.urls import path

from .views import (
    ApplyCodeProposalView,
    CodeDownloadView,
    GenerationChatPostView,
    GenerationChatThreadView,
    GenerationCreateView,
    GenerationDetailView,
    GenerationStatusView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectListView,
    ProjectUpdateView,
)

app_name = "builder"

urlpatterns = [
    path("", ProjectListView.as_view(), name="list"),
    path("new/", ProjectCreateView.as_view(), name="create"),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", ProjectUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/generate/", GenerationCreateView.as_view(), name="generate"),
    path(
        "<uuid:pk>/generations/<uuid:generation_pk>/",
        GenerationDetailView.as_view(),
        name="generation-detail",
    ),
    path(
        "<uuid:pk>/generations/<uuid:generation_pk>/status/",
        GenerationStatusView.as_view(),
        name="generation-status",
    ),
    path(
        "<uuid:pk>/versions/<uuid:version_pk>/download/",
        CodeDownloadView.as_view(),
        name="download",
    ),
    path(
        "<uuid:pk>/generations/<uuid:generation_pk>/chat/",
        GenerationChatPostView.as_view(),
        name="generation-chat",
    ),
    path(
        "<uuid:pk>/generations/<uuid:generation_pk>/chat/thread/",
        GenerationChatThreadView.as_view(),
        name="generation-chat-thread",
    ),
    path(
        "<uuid:pk>/generations/<uuid:generation_pk>/proposals/<uuid:proposal_pk>/apply/",
        ApplyCodeProposalView.as_view(),
        name="apply-proposal",
    ),
]

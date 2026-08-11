from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from apps.core.mixins import OwnedQuerySetMixin, OwnerFormMixin

from .forms import GenerationChatForm, GenerationRequestForm, ProjectForm
from .models import CodeRevisionProposal, CodeVersion, Generation, GenerationChatMessage, Project
from .services.chat import dispatch_chat_response
from .services.generation import (
    GenerationUnavailableError,
    create_generation,
    dispatch_generation,
    find_published_workflow,
)
from .services.revisions import ProposalApplicationError, apply_code_proposal


def _generation_chat_anchor(project_id, generation_id) -> str:
    url = reverse(
        "builder:generation-detail",
        kwargs={"pk": project_id, "generation_pk": generation_id},
    )
    return f"{url}#generation-chat"


class ProjectListView(OwnedQuerySetMixin, ListView):
    model = Project
    template_name = "builder/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return super().get_queryset().active()


class ProjectCreateView(OwnerFormMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "builder/project_form.html"

    def get_success_url(self):
        return reverse("builder:detail", kwargs={"pk": self.object.pk})


class ProjectDetailView(OwnedQuerySetMixin, DetailView):
    model = Project
    template_name = "builder/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_version"] = self.object.latest_code_version
        context["latest_generation"] = self.object.generations.first()
        context["workflow_ready"] = find_published_workflow(self.object.artifact_type) is not None
        context["versions"] = self.object.code_versions.all()[:10]
        return context


class ProjectUpdateView(OwnedQuerySetMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "builder/project_form.html"

    def get_success_url(self):
        return reverse("builder:detail", kwargs={"pk": self.object.pk})


class GenerationCreateView(LoginRequiredMixin, FormView):
    form_class = GenerationRequestForm
    template_name = "builder/generation_form.html"
    project: Project

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs["pk"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["prompt"] = self.project.description
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        context["workflow"] = find_published_workflow(self.project.artifact_type)
        return context

    def form_valid(self, form):
        active = self.project.generations.filter(
            status__in=(Generation.Status.QUEUED, Generation.Status.RUNNING)
        ).first()
        if active is not None:
            messages.info(self.request, "This project already has an active generation run.")
            return redirect(
                "builder:generation-detail", pk=self.project.pk, generation_pk=active.pk
            )

        try:
            generation = create_generation(self.project, form.cleaned_data["prompt"])
        except GenerationUnavailableError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        dispatch_generation(generation)
        messages.success(self.request, "Generation started. The run is pinned to its AI workflow.")
        return redirect(
            "builder:generation-detail",
            pk=self.project.pk,
            generation_pk=generation.pk,
        )


class OwnedGenerationMixin(LoginRequiredMixin):
    def get_queryset(self):
        return Generation.objects.select_related("project", "workflow").filter(
            project_id=self.kwargs["pk"], project__owner=self.request.user
        )


class GenerationDetailView(OwnedGenerationMixin, DetailView):
    model = Generation
    pk_url_kwarg = "generation_pk"
    context_object_name = "generation"
    template_name = "builder/generation_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["code_version"] = self.object.project.latest_code_version
        context["chat_form"] = GenerationChatForm()
        context["chat_messages"] = self.object.chat_messages.select_related(
            "author", "proposal__base_version", "proposal__applied_version"
        ).all()
        context["chat_has_pending"] = self.object.chat_messages.filter(
            status__in=(
                GenerationChatMessage.Status.PENDING,
                GenerationChatMessage.Status.RUNNING,
            )
        ).exists()
        return context


class GenerationStatusView(GenerationDetailView):
    template_name = "builder/partials/generation_status.html"


class CodeDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk, version_pk):
        code_version = get_object_or_404(
            CodeVersion.objects.select_related("project"),
            pk=version_pk,
            project_id=pk,
            project__owner=request.user,
        )
        filename = Path(code_version.filename).name.replace('"', "")
        response = HttpResponse(code_version.source_code, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class GenerationChatPostView(LoginRequiredMixin, View):
    def post(self, request, pk, generation_pk):
        generation = get_object_or_404(
            Generation.objects.select_related("project"),
            pk=generation_pk,
            project_id=pk,
            project__owner=request.user,
        )
        form = GenerationChatForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Enter a valid copilot message.")
            return redirect(_generation_chat_anchor(pk, generation_pk))
        if generation.chat_messages.filter(
            role=GenerationChatMessage.Role.ASSISTANT,
            status__in=(
                GenerationChatMessage.Status.PENDING,
                GenerationChatMessage.Status.RUNNING,
            ),
        ).exists():
            messages.info(request, "The copilot is already responding to this generation.")
            return redirect(_generation_chat_anchor(pk, generation_pk))

        with transaction.atomic():
            GenerationChatMessage.objects.create(
                generation=generation,
                author=request.user,
                role=GenerationChatMessage.Role.USER,
                status=GenerationChatMessage.Status.COMPLETED,
                content=form.cleaned_data["message"],
            )
            assistant_message = GenerationChatMessage.objects.create(
                generation=generation,
                role=GenerationChatMessage.Role.ASSISTANT,
                status=GenerationChatMessage.Status.PENDING,
            )
        dispatch_chat_response(assistant_message)
        return redirect(_generation_chat_anchor(pk, generation_pk))


class GenerationChatThreadView(GenerationDetailView):
    template_name = "builder/partials/generation_chat.html"


class ApplyCodeProposalView(LoginRequiredMixin, View):
    def post(self, request, pk, generation_pk, proposal_pk):
        proposal = get_object_or_404(
            CodeRevisionProposal.objects.select_related("generation__project"),
            pk=proposal_pk,
            generation_id=generation_pk,
            generation__project_id=pk,
            generation__project__owner=request.user,
        )
        try:
            code_version = apply_code_proposal(proposal)
        except ProposalApplicationError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Copilot proposal applied as version {code_version.version}. "
                f"Validation: {code_version.get_validation_status_display()}.",
            )
        return redirect(_generation_chat_anchor(pk, generation_pk))

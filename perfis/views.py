import base64
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from PIL import Image, ImageOps

from financeiro.constants import THEME_CHOICES
from gastos.models import Categoria
from gastos.services import get_dashboard_data
from perfis.decorators import active_profile_required
from perfis.forms import LoginForm, ProfileImageForm, RendaExtraForm, SalaryUpdateForm
from perfis.models import Perfil
from perfis.services import (
    clear_profile_image,
    clear_active_profile,
    get_active_profile,
    list_profiles,
    set_active_profile,
    set_profile_extra_sections_visibility,
    set_profile_image,
    set_profile_theme,
)


AVAILABLE_THEMES = {value for value, _ in THEME_CHOICES}


def get_safe_redirect(request, fallback=None):
    redirect_to = request.POST.get("next") or fallback or reverse("dashboard")
    if not url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return fallback or reverse("dashboard")
    return redirect_to


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard" if get_active_profile(request) else "select_profile")

    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        clear_active_profile(request)
        messages.success(request, "Login realizado. Escolha o perfil que deseja abrir.")
        return redirect("select_profile")

    return render(request, "perfis/login.html", {"form": form})


@login_required
def select_profile(request):
    profiles = list_profiles().prefetch_related("parcelas_salariais")

    if request.method == "POST":
        profile = get_object_or_404(Perfil, slug=request.POST.get("profile_slug"))
        set_active_profile(request, profile)
        messages.success(request, f"Perfil {profile.nome} ativado.")
        return redirect("dashboard")

    return render(
        request,
        "perfis/select_profile.html",
        {
            "profiles": profiles,
        },
    )


@active_profile_required
def dashboard(request):
    profile = get_active_profile(request)
    salary_form = SalaryUpdateForm(profile=profile, prefix="salary")
    extra_form = RendaExtraForm(prefix="extra")
    context = get_dashboard_data(profile, filters=request.GET)
    context.update(
        {
            "profile": profile,
            "salary_form": salary_form,
            "extra_form": extra_form,
            "categories": Categoria.objects.order_by("nome"),
        }
    )
    return render(request, "perfis/dashboard.html", context)


@active_profile_required
def update_salary(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    form = SalaryUpdateForm(request.POST, profile=profile, prefix="salary")
    if form.is_valid():
        form.save()
        messages.success(request, "Recebimentos fixos atualizados.")
    else:
        messages.error(request, "Revise os valores do salario antes de salvar.")
    return redirect("dashboard")


@active_profile_required
def add_extra_income(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    form = RendaExtraForm(request.POST, prefix="extra")
    if form.is_valid():
        renda_extra = form.save(commit=False)
        renda_extra.perfil = profile
        renda_extra.save()
        messages.success(request, "Renda extra adicionada.")
    else:
        messages.error(request, "Nao foi possivel salvar a renda extra.")
    return redirect("dashboard")


@active_profile_required
def update_theme(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    theme = request.POST.get("theme")
    redirect_to = get_safe_redirect(request)

    if theme not in AVAILABLE_THEMES:
        messages.error(request, "Tema invalido.")
        return redirect(redirect_to)

    set_profile_theme(profile, theme)
    messages.success(request, f"Tema {theme.title()} salvo para o perfil.")
    return redirect(redirect_to)


@active_profile_required
def toggle_extra_sections(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    redirect_to = get_safe_redirect(request)
    show_extra_sections = request.POST.get("mostrar_funcoes_extras") == "1"

    set_profile_extra_sections_visibility(profile, show_extra_sections)
    if show_extra_sections:
        messages.success(request, "Funcoes extras exibidas novamente.")
    else:
        messages.success(request, "Funcoes extras ocultadas para este perfil.")
    return redirect(redirect_to)


@active_profile_required
def update_profile_image(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    redirect_to = get_safe_redirect(request)
    form = ProfileImageForm(request.POST, request.FILES)

    if not form.is_valid():
        messages.error(request, "Escolha uma imagem valida para atualizar o perfil.")
        return redirect(redirect_to)

    uploaded_image = form.cleaned_data["image"]
    try:
        image = Image.open(uploaded_image)
        image = ImageOps.exif_transpose(image)
        image.thumbnail((320, 320))

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        output = BytesIO()
        image.save(output, format="WEBP", quality=82, method=6)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
    except Exception:
        messages.error(request, "Nao foi possivel processar a imagem enviada.")
        return redirect(redirect_to)

    set_profile_image(profile, f"data:image/webp;base64,{encoded}")
    messages.success(request, "Foto de perfil atualizada.")
    return redirect(redirect_to)


@active_profile_required
def remove_profile_image(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    redirect_to = get_safe_redirect(request)
    clear_profile_image(profile)
    messages.success(request, "Foto de perfil removida.")
    return redirect(redirect_to)


def logout_view(request):
    clear_active_profile(request)
    auth_logout(request)
    messages.info(request, "Sua sessao foi encerrada.")
    return redirect("login")

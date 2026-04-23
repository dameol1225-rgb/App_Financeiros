import base64
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from PIL import Image, ImageOps

from financeiro.constants import THEME_CHOICES
from financeiro.utils import month_bounds
from gastos.models import Categoria
from gastos.services import get_dashboard_data
from perfis.decorators import active_profile_required
from perfis.forms import LoginForm, ProfileImageForm, RendaExtraForm, SalaryUpdateForm
from perfis.models import Perfil, RendaExtra
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


def get_selected_period(request, today):
    try:
        month = int(request.GET.get("mes", today.month))
    except (TypeError, ValueError):
        month = today.month

    try:
        year = int(request.GET.get("ano", today.year))
    except (TypeError, ValueError):
        year = today.year

    if month not in range(1, 13):
        month = today.month

    return year, month


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard" if get_active_profile(request) else "select_profile")

    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        clear_active_profile(request)
        return redirect("select_profile")

    return render(request, "perfis/login.html", {"form": form})


@login_required
def select_profile(request):
    profiles = list_profiles().prefetch_related("parcelas_salariais")

    if request.method == "POST":
        profile = get_object_or_404(Perfil, slug=request.POST.get("profile_slug"))
        set_active_profile(request, profile)
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
    context = get_dashboard_data(profile, filters=request.GET)
    context.update(
        {
            "profile": profile,
            "categories": Categoria.objects.order_by("nome"),
        }
    )
    return render(request, "perfis/dashboard.html", context)


@active_profile_required
def extra_income_page(request):
    profile = get_active_profile(request)
    today = timezone.localdate()
    selected_year, selected_month = get_selected_period(request, today)
    reference_start, reference_end = month_bounds(selected_year, selected_month)
    extra_income = list(
        profile.rendas_extras.filter(data__range=(reference_start, reference_end)).order_by("-data", "-criado_em")
    )
    extra_total = sum((item.valor for item in extra_income), start=Decimal("0.00"))

    year_values = set(profile.rendas_extras.values_list("data__year", flat=True))
    year_values.discard(None)
    year_values.add(today.year)
    year_values.add(selected_year)

    return render(
        request,
        "perfis/extra_income.html",
        {
            "profile": profile,
            "form": RendaExtraForm(prefix="extra"),
            "extra_income": extra_income,
            "extra_total": extra_total,
            "selected_month": selected_month,
            "selected_year": selected_year,
            "month_options": range(1, 13),
            "year_options": sorted(year_values, reverse=True),
            "reference_start": reference_start,
            "reference_end": reference_end,
        },
    )


@active_profile_required
def profile_settings(request):
    profile = get_active_profile(request)
    context = {
        "profile": profile,
        "salary_form": SalaryUpdateForm(profile=profile, prefix="salary"),
    }
    return render(request, "perfis/profile_settings.html", context)


@active_profile_required
def more_menu(request):
    profile = get_active_profile(request)
    return render(request, "perfis/more.html", {"profile": profile})


@active_profile_required
def update_salary(request):
    if request.method != "POST":
        return redirect("profile_settings")

    profile = get_active_profile(request)
    form = SalaryUpdateForm(request.POST, profile=profile, prefix="salary")
    redirect_to = get_safe_redirect(request, fallback=reverse("profile_settings"))
    if form.is_valid():
        form.save()
        messages.success(request, "Recebimentos fixos atualizados.")
    else:
        messages.error(request, "Revise os valores do salario antes de salvar.")
    return redirect(redirect_to)


@active_profile_required
def add_extra_income(request):
    if request.method != "POST":
        return redirect("extra_income_page")

    profile = get_active_profile(request)
    form = RendaExtraForm(request.POST, prefix="extra")
    redirect_to = get_safe_redirect(request, fallback=reverse("extra_income_page"))
    if form.is_valid():
        renda_extra = form.save(commit=False)
        renda_extra.perfil = profile
        renda_extra.save()
        messages.success(request, "Renda extra adicionada.")
    else:
        messages.error(request, "Não foi possível salvar a renda extra.")
    return redirect(redirect_to)


@active_profile_required
def edit_extra_income(request, extra_income_id):
    profile = get_active_profile(request)
    extra_income = get_object_or_404(RendaExtra, pk=extra_income_id, perfil=profile)

    form = RendaExtraForm(request.POST or None, instance=extra_income)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Renda extra atualizada.")
            return redirect(get_safe_redirect(request, fallback=reverse("extra_income_page")))
        messages.error(request, "Não foi possível salvar as alterações da renda extra.")

    return render(
        request,
        "perfis/edit_extra_income.html",
        {
            "profile": profile,
            "form": form,
            "extra_income": extra_income,
        },
    )


@active_profile_required
def delete_extra_income(request, extra_income_id):
    if request.method != "POST":
        return redirect("extra_income_page")

    profile = get_active_profile(request)
    extra_income = get_object_or_404(RendaExtra, pk=extra_income_id, perfil=profile)
    extra_income.delete()
    messages.success(request, "Renda extra removida.")
    return redirect(get_safe_redirect(request, fallback=reverse("extra_income_page")))


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
        messages.success(request, "Funções extras ocultadas para este perfil.")
    return redirect(redirect_to)


@active_profile_required
def update_profile_image(request):
    if request.method != "POST":
        return redirect("dashboard")

    profile = get_active_profile(request)
    redirect_to = get_safe_redirect(request)
    form = ProfileImageForm(request.POST, request.FILES)

    if not form.is_valid():
        messages.error(request, "Escolha uma imagem válida para atualizar o perfil.")
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
        messages.error(request, "Não foi possível processar a imagem enviada.")
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


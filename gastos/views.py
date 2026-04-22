from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gastos.forms import GastoForm
from gastos.models import Categoria, Gasto
from gastos.services import (
    create_gasto_for_profile,
    delete_gasto_for_profile,
    get_gastos_for_profile,
    get_history_data,
    get_print_preview_data,
    mark_next_installment_paid,
    undo_last_installment_payment,
    update_gasto_for_profile,
)
from perfis.decorators import active_profile_required
from perfis.services import get_active_profile


@active_profile_required
def gastos_list(request):
    profile = get_active_profile(request)
    gastos = get_gastos_for_profile(profile)
    return render(
        request,
        "gastos/gastos.html",
        {
            "profile": profile,
            "gastos": gastos,
        },
    )


@active_profile_required
def add_gasto(request):
    profile = get_active_profile(request)
    form = GastoForm(request.POST or None)
    form.fields["categoria"].queryset = Categoria.objects.order_by("nome")

    if request.method == "POST" and form.is_valid():
        create_gasto_for_profile(profile, form.cleaned_data)
        messages.success(request, "Gasto criado e parcelas geradas com sucesso.")
        return redirect("gastos")

    return render(
        request,
        "gastos/adicionar_gasto.html",
        {
            "form": form,
            "profile": profile,
            "is_edit_mode": False,
        },
    )


@active_profile_required
def edit_gasto(request, gasto_id):
    profile = get_active_profile(request)
    gasto = get_object_or_404(Gasto, pk=gasto_id, perfil=profile)
    form = GastoForm(request.POST or None, instance=gasto)
    form.fields["categoria"].queryset = Categoria.objects.order_by("nome")

    if request.method == "POST" and form.is_valid():
        update_gasto_for_profile(gasto, form.cleaned_data)
        messages.success(request, "Gasto atualizado e salvo no banco com sucesso.")
        return redirect("gastos")

    return render(
        request,
        "gastos/adicionar_gasto.html",
        {
            "form": form,
            "profile": profile,
            "gasto": gasto,
            "is_edit_mode": True,
        },
    )


@active_profile_required
def delete_gasto(request, gasto_id):
    if request.method != "POST":
        return redirect("gastos")

    profile = get_active_profile(request)
    gasto = get_object_or_404(Gasto, pk=gasto_id, perfil=profile)
    gasto_nome = gasto.nome
    delete_gasto_for_profile(gasto)
    messages.success(request, f"Gasto {gasto_nome} removido com sucesso.")
    return redirect("gastos")


@active_profile_required
def mark_next_payment(request, gasto_id):
    if request.method != "POST":
        return redirect("gastos")

    profile = get_active_profile(request)
    gasto = get_object_or_404(Gasto, pk=gasto_id, perfil=profile)
    parcela = mark_next_installment_paid(gasto)
    if parcela:
        messages.success(request, f"Parcela {parcela.numero} marcada como paga.")
    else:
        messages.info(request, "Esse gasto ja esta quitado.")
    return redirect("gastos")


@active_profile_required
def undo_payment(request, gasto_id):
    if request.method != "POST":
        return redirect("gastos")

    profile = get_active_profile(request)
    gasto = get_object_or_404(Gasto, pk=gasto_id, perfil=profile)
    parcela = undo_last_installment_payment(gasto)
    if parcela:
        messages.success(request, f"Pagamento da parcela {parcela.numero} desfeito.")
    else:
        messages.info(request, "Nao ha pagamento para desfazer.")
    return redirect("gastos")


@active_profile_required
def historico(request):
    profile = get_active_profile(request)
    today = timezone.localdate()

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

    category_id = request.GET.get("categoria") or None
    status = request.GET.get("status") or None
    history_data = get_history_data(profile, year, month, category_id=category_id, status=status)

    return render(
        request,
        "gastos/historico.html",
        {
            "profile": profile,
            "categories": Categoria.objects.order_by("nome"),
            "selected_month": month,
            "selected_year": year,
            "selected_category": category_id,
            "selected_status": status,
            "month_options": range(1, 13),
            "year_options": range(today.year - 2, today.year + 3),
            "status_options": Gasto.Status.choices,
            **history_data,
        },
    )


@active_profile_required
def export_pdf(request):
    profile = get_active_profile(request)
    return render(
        request,
        "gastos/print_preview.html",
        get_print_preview_data(profile),
    )


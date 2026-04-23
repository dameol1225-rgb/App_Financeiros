from collections import defaultdict
from decimal import Decimal
import unicodedata

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from financeiro.constants import (
    CATEGORY_PALETTE,
    DUE_DAY_CHOICES,
    INSTALLMENT_FILTER_STATUS_CHOICES,
)
from financeiro.utils import add_months, month_bounds, next_due_date, quantize_money
from gastos.models import Gasto, Parcela


ZERO = Decimal("0.00")
MONTH_LABELS = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)


def parse_int(value, default, *, min_value=None, max_value=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    if min_value is not None and parsed < min_value:
        return default
    if max_value is not None and parsed > max_value:
        return default
    return parsed


def split_installments(total_amount, total_installments):
    total_amount = quantize_money(total_amount)
    base_value = (total_amount / Decimal(total_installments)).quantize(Decimal("0.01"))
    values = [base_value for _ in range(total_installments)]
    difference = total_amount - sum(values, start=ZERO)
    if values:
        values[-1] = quantize_money(values[-1] + difference)
    return values


def normalize_expense_name(name):
    compact_name = " ".join((name or "").split())
    normalized = unicodedata.normalize("NFKD", compact_name)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.casefold()


def sync_gasto_status(gasto):
    has_pending = gasto.parcelas.filter(status=Parcela.Status.PENDENTE).exists()
    new_status = Gasto.Status.ATIVO if has_pending else Gasto.Status.QUITADO
    if gasto.status != new_status:
        gasto.status = new_status
        gasto.save(update_fields=["status", "atualizado_em"])
    return gasto


@transaction.atomic
def generate_installments(gasto, preserve_paid_count=0):
    preserve_paid_count = max(0, min(int(preserve_paid_count), gasto.quantidade_parcelas))
    gasto.parcelas.all().delete()
    values = split_installments(gasto.valor_total, gasto.quantidade_parcelas)
    due_date = next_due_date(gasto.data_inicio, gasto.dia_vencimento)

    parcels = []
    for index, value in enumerate(values, start=1):
        parcels.append(
            Parcela(
                gasto=gasto,
                numero=index,
                valor=value,
                data_vencimento=due_date,
                status=(
                    Parcela.Status.PAGO if index <= preserve_paid_count else Parcela.Status.PENDENTE
                ),
            )
        )
        due_date = add_months(due_date, 1, gasto.dia_vencimento)

    Parcela.objects.bulk_create(parcels)
    sync_gasto_status(gasto)
    return gasto


@transaction.atomic
def create_gasto_for_profile(profile, cleaned_data):
    gasto = Gasto.objects.create(perfil=profile, **cleaned_data)
    generate_installments(gasto)
    return gasto


@transaction.atomic
def update_gasto_for_profile(gasto, cleaned_data):
    paid_count = gasto.parcelas.filter(status=Parcela.Status.PAGO).count()
    for field, value in cleaned_data.items():
        setattr(gasto, field, value)
    gasto.save()
    generate_installments(gasto, preserve_paid_count=paid_count)
    return gasto


@transaction.atomic
def delete_gasto_for_profile(gasto):
    gasto.delete()


def mark_next_installment_paid(gasto):
    parcela = gasto.parcelas.filter(status=Parcela.Status.PENDENTE).order_by("numero").first()
    if parcela:
        parcela.status = Parcela.Status.PAGO
        parcela.save(update_fields=["status"])
        sync_gasto_status(gasto)
    return parcela


def undo_last_installment_payment(gasto):
    parcela = gasto.parcelas.filter(status=Parcela.Status.PAGO).order_by("-numero").first()
    if parcela:
        parcela.status = Parcela.Status.PENDENTE
        parcela.save(update_fields=["status"])
        sync_gasto_status(gasto)
    return parcela


def get_category_color(label, index):
    return CATEGORY_PALETTE[index % len(CATEGORY_PALETTE)]


def build_category_breakdown(category_totals):
    ordered = sorted(category_totals.items(), key=lambda item: (-item[1], item[0].lower()))
    total = sum((value for _, value in ordered), start=ZERO)

    breakdown = []
    for index, (label, value) in enumerate(ordered):
        share = ZERO
        if total > ZERO:
            share = quantize_money((value / total) * Decimal("100"))
        breakdown.append(
            {
                "label": label,
                "value": value,
                "share": share,
                "color": get_category_color(label, index),
            }
        )

    return breakdown


def serialize_gasto_card(gasto):
    parcelas = list(gasto.parcelas.all())
    pending = [item for item in parcelas if item.status == Parcela.Status.PENDENTE]
    paid_count = len(parcelas) - len(pending)
    total_count = len(parcelas)
    progress = ZERO
    if total_count:
        progress = quantize_money((Decimal(paid_count) / Decimal(total_count)) * Decimal("100"))

    current_parcela = pending[0] if pending else (parcelas[-1] if parcelas else None)
    remaining_total = sum((item.valor for item in pending), start=ZERO)

    return {
        "gasto": gasto,
        "paid_count": paid_count,
        "pending_count": len(pending),
        "total_count": total_count,
        "progress_percentage": progress,
        "monthly_value": current_parcela.valor if current_parcela else ZERO,
        "next_due_date": current_parcela.data_vencimento if current_parcela else None,
        "remaining_total": remaining_total,
        "remaining_count": len(pending),
    }


def serialize_grouped_debt_cards(gastos):
    grouped_cards = {}

    for gasto in gastos:
        card = serialize_gasto_card(gasto)
        key = normalize_expense_name(gasto.nome)
        if not key:
            continue

        group = grouped_cards.setdefault(
            key,
            {
                "nome": gasto.nome,
                "categoria_nome": gasto.categoria.nome,
                "status_value": Gasto.Status.ATIVO,
                "status_label": Gasto.Status.ATIVO.label,
                "paid_count": 0,
                "total_count": 0,
                "remaining_count": 0,
                "remaining_total": ZERO,
                "monthly_value": ZERO,
                "next_due_date": None,
                "items_count": 0,
            },
        )

        group["paid_count"] += card["paid_count"]
        group["total_count"] += card["total_count"]
        group["remaining_count"] += card["remaining_count"]
        group["remaining_total"] += card["remaining_total"]
        group["monthly_value"] += card["monthly_value"]
        group["items_count"] += 1

        next_due_date = card["next_due_date"]
        if next_due_date and (group["next_due_date"] is None or next_due_date < group["next_due_date"]):
            group["next_due_date"] = next_due_date

    serialized_groups = []
    for group in grouped_cards.values():
        progress = ZERO
        if group["total_count"]:
            progress = quantize_money(
                (Decimal(group["paid_count"]) / Decimal(group["total_count"])) * Decimal("100")
            )
        group["progress_percentage"] = progress
        serialized_groups.append(group)

    serialized_groups.sort(
        key=lambda item: (
            item["next_due_date"] is None,
            item["next_due_date"] or timezone.localdate(),
            item["nome"].lower(),
        )
    )
    return serialized_groups


def build_due_buckets(parcels):
    buckets = []
    for day, label in DUE_DAY_CHOICES:
        bucket_parcels = [item for item in parcels if item.data_vencimento.day == day]
        buckets.append(
            {
                "day": day,
                "label": label,
                "total": sum((item.valor for item in bucket_parcels), start=ZERO),
                "count": len(bucket_parcels),
                "items": bucket_parcels,
            }
        )
    return buckets


def build_annual_expense_chart(profile, filters, today):
    filters = filters or {}
    selected_year = parse_int(
        filters.get("annual_ano"),
        today.year,
        min_value=today.year - 10,
        max_value=today.year + 2,
    )

    year_values = set(
        Parcela.objects.filter(gasto__perfil=profile).values_list("data_vencimento__year", flat=True)
    )
    year_values.discard(None)
    year_values.add(today.year)
    year_values.add(selected_year)
    year_options = sorted(year_values, reverse=True)

    monthly_totals = [ZERO for _ in range(12)]
    annual_parcels = Parcela.objects.filter(
        gasto__perfil=profile,
        data_vencimento__year=selected_year,
    ).order_by("data_vencimento", "numero")

    for parcela in annual_parcels:
        monthly_totals[parcela.data_vencimento.month - 1] += parcela.valor

    return {
        "selected_annual_year": selected_year,
        "annual_year_options": year_options,
        "annual_expense_total": sum(monthly_totals, start=ZERO),
        "annual_expense_chart": {
            "labels": list(MONTH_LABELS),
            "values": [float(value) for value in monthly_totals],
        },
    }


def get_month_status(projected_balance, commitment_total):
    if projected_balance > ZERO and commitment_total <= Decimal("70"):
        return {
            "label": "Mês no verde",
            "tone": "positive",
            "message": "",
        }
    if projected_balance >= ZERO:
        return {
            "label": "Mês em atenção",
            "tone": "warning",
            "message": "",
        }
    return {
        "label": "Mês apertado",
        "tone": "danger",
        "message": "",
    }


def build_due_filter_data(profile, filters, today):
    filters = filters or {}
    due_month = parse_int(filters.get("due_mes"), today.month, min_value=1, max_value=12)
    due_year = parse_int(filters.get("due_ano"), today.year, min_value=today.year - 3, max_value=today.year + 5)
    requested_due_category = filters.get("due_categoria") or ""
    due_category_id = parse_int(requested_due_category, None, min_value=1)
    selected_due_status = filters.get("due_status") or Parcela.Status.PENDENTE

    allowed_statuses = {Parcela.Status.PENDENTE, Parcela.Status.PAGO, "todos"}
    if selected_due_status not in allowed_statuses:
        selected_due_status = Parcela.Status.PENDENTE

    due_start, due_end = month_bounds(due_year, due_month)
    due_queryset = Parcela.objects.select_related("gasto", "gasto__categoria").filter(
        gasto__perfil=profile,
        data_vencimento__range=(due_start, due_end),
    )

    if due_category_id:
        due_queryset = due_queryset.filter(gasto__categoria_id=due_category_id)
    if selected_due_status != "todos":
        due_queryset = due_queryset.filter(status=selected_due_status)

    due_installments = list(due_queryset.order_by("data_vencimento", "numero", "gasto__nome"))
    due_total = sum((item.valor for item in due_installments), start=ZERO)
    unique_gastos = len({item.gasto_id for item in due_installments})

    return {
        "due_reference_start": due_start,
        "due_reference_end": due_end,
        "selected_due_month": due_month,
        "selected_due_year": due_year,
        "selected_due_category": str(due_category_id or ""),
        "selected_due_status": selected_due_status,
        "due_month_options": range(1, 13),
        "due_year_options": range(today.year - 2, today.year + 4),
        "due_status_options": INSTALLMENT_FILTER_STATUS_CHOICES,
        "due_installments": due_installments,
        "due_installments_total": due_total,
        "due_installments_count": len(due_installments),
        "due_gastos_count": unique_gastos,
        "due_buckets": build_due_buckets(due_installments),
    }


def get_dashboard_data(profile, filters=None, today=None):
    today = today or timezone.localdate()
    month_start, month_end = month_bounds(today.year, today.month)

    salary_items = list(profile.parcelas_salariais.order_by("dia_recebimento"))
    salary_total = sum((item.valor for item in salary_items), start=ZERO)
    extra_income = list(profile.rendas_extras.filter(data__range=(month_start, month_end)))
    extra_total = sum((item.valor for item in extra_income), start=ZERO)

    month_parcels = list(
        Parcela.objects.select_related("gasto", "gasto__categoria")
        .filter(gasto__perfil=profile, data_vencimento__range=(month_start, month_end))
        .order_by("data_vencimento", "numero")
    )
    expense_total = sum((item.valor for item in month_parcels), start=ZERO)
    total_income = salary_total + extra_total
    projected_balance = total_income - expense_total

    active_gastos_qs = (
        profile.gastos.select_related("categoria")
        .prefetch_related("parcelas")
        .filter(status=Gasto.Status.ATIVO)
        .order_by("dia_vencimento", "nome")
    )
    debt_cards = serialize_grouped_debt_cards(active_gastos_qs)

    category_totals = defaultdict(lambda: ZERO)
    for parcela in month_parcels:
        category_totals[parcela.gasto.categoria.nome] += parcela.valor
    category_breakdown = build_category_breakdown(category_totals)
    top_category = category_breakdown[0] if category_breakdown else None

    salary_commitment = ZERO
    if salary_total > ZERO:
        salary_commitment = quantize_money((expense_total / salary_total) * Decimal("100"))

    income_commitment = ZERO
    available_ratio = ZERO
    if total_income > ZERO:
        income_commitment = quantize_money((expense_total / total_income) * Decimal("100"))
        available_ratio = quantize_money((projected_balance / total_income) * Decimal("100"))

    due_filter_data = build_due_filter_data(profile, filters, today)
    annual_chart_data = build_annual_expense_chart(profile, filters, today)

    return {
        "reference_date": today,
        "salary_items": salary_items,
        "salary_total": salary_total,
        "extra_total": extra_total,
        "expense_total": expense_total,
        "total_income": total_income,
        "projected_balance": projected_balance,
        "commitment_percentage": salary_commitment,
        "income_commitment_percentage": income_commitment,
        "available_ratio": available_ratio,
        "month_status": get_month_status(projected_balance, income_commitment),
        "debt_cards": debt_cards,
        "extra_income": extra_income,
        "category_breakdown": category_breakdown,
        "top_category": top_category,
        "expense_chart": {
            "labels": [item["label"] for item in category_breakdown],
            "values": [float(item["value"]) for item in category_breakdown],
            "colors": [item["color"] for item in category_breakdown],
        },
        **due_filter_data,
        **annual_chart_data,
    }


def get_gastos_for_profile(profile):
    gastos = (
        profile.gastos.select_related("categoria")
        .prefetch_related("parcelas")
        .order_by("status", "dia_vencimento", "nome")
    )

    cards = []
    for gasto in gastos:
        sync_gasto_status(gasto)
        cards.append(serialize_gasto_card(gasto))
    return cards


def get_history_data(profile, year, month, category_id=None, status=None):
    month_start, month_end = month_bounds(year, month)
    gastos = profile.gastos.select_related("categoria").prefetch_related(
        Prefetch("parcelas", queryset=Parcela.objects.order_by("numero"))
    )

    if category_id:
        gastos = gastos.filter(categoria_id=category_id)
    if status:
        gastos = gastos.filter(status=status)

    entries = []
    category_totals = defaultdict(lambda: ZERO)
    for gasto in gastos:
        parcelas = list(gasto.parcelas.all())
        period_parcels = [
            parcela for parcela in parcelas if month_start <= parcela.data_vencimento <= month_end
        ]
        if not period_parcels:
            continue

        period_total = sum((parcela.valor for parcela in period_parcels), start=ZERO)
        pending_count = len([parcela for parcela in parcelas if parcela.status == Parcela.Status.PENDENTE])
        next_pending = next(
            (parcela.data_vencimento for parcela in parcelas if parcela.status == Parcela.Status.PENDENTE),
            None,
        )

        entries.append(
            {
                "gasto": gasto,
                "period_total": period_total,
                "parcel_count": len(period_parcels),
                "remaining_count": pending_count,
                "next_pending": next_pending,
            }
        )
        category_totals[gasto.categoria.nome] += period_total

    entries.sort(key=lambda item: (-item["period_total"], item["gasto"].nome.lower()))

    category_breakdown = build_category_breakdown(category_totals)
    period_total = sum((item["period_total"] for item in entries), start=ZERO)
    average_ticket = ZERO
    if entries:
        average_ticket = quantize_money(period_total / Decimal(len(entries)))

    return {
        "reference_start": month_start,
        "reference_end": month_end,
        "entries": entries,
        "period_total": period_total,
        "average_ticket": average_ticket,
        "top_category": category_breakdown[0] if category_breakdown else None,
        "category_breakdown": category_breakdown,
        "chart": {
            "labels": [item["label"] for item in category_breakdown],
            "values": [float(item["value"]) for item in category_breakdown],
            "colors": [item["color"] for item in category_breakdown],
        },
    }


def get_print_preview_data(profile):
    today = timezone.localdate()
    dashboard = get_dashboard_data(profile, today=today)
    gastos = get_gastos_for_profile(profile)

    return {
        "profile": profile,
        "generated_at": today,
        "salary_items": profile.parcelas_salariais.order_by("dia_recebimento"),
        "extra_income": profile.rendas_extras.order_by("-data", "-criado_em"),
        "gastos": gastos,
        "summary": dashboard,
    }


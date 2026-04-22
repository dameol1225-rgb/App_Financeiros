from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from financeiro.constants import DEFAULT_CATEGORIES, DEFAULT_PROFILES, DEFAULT_SALARY_VALUE
from financeiro.utils import add_months
from gastos.models import Categoria
from perfis.models import Perfil, RendaExtra, SalarioParcela


def list_profiles():
    return Perfil.objects.order_by("ordem", "nome")


def get_active_profile(request):
    profile_id = request.session.get("active_profile_id")
    if not profile_id:
        return None

    try:
        return Perfil.objects.get(pk=profile_id)
    except Perfil.DoesNotExist:
        request.session.pop("active_profile_id", None)
        return None


def set_active_profile(request, profile):
    request.session["active_profile_id"] = profile.pk


def clear_active_profile(request):
    request.session.pop("active_profile_id", None)


def set_profile_theme(profile, theme):
    profile.tema = theme
    profile.save(update_fields=["tema"])
    return profile


def get_profile_history_anchor(profile):
    gasto_anchor = profile.gastos.order_by("data_inicio").values_list("data_inicio", flat=True).first()
    extra_anchor = profile.rendas_extras.order_by("data").values_list("data", flat=True).first()

    anchors = [item for item in (gasto_anchor, extra_anchor) if item]
    return min(anchors) if anchors else None


def get_cleanup_notice(profile, today=None):
    today = today or timezone.localdate()
    anchor = get_profile_history_anchor(profile)
    if not anchor:
        return None

    cleanup_date = add_months(anchor, 12)
    warning_start = cleanup_date - timedelta(days=30)
    if today < warning_start:
        return None

    return {
        "cleanup_date": cleanup_date,
        "days_left": max((cleanup_date - today).days, 0),
    }


def ensure_default_setup(reset_password=False):
    user_model = get_user_model()
    username = settings.CASAL_ORGANIZADO_USERNAME
    password = settings.CASAL_ORGANIZADO_PASSWORD

    user, created = user_model.objects.get_or_create(
        username=username,
        defaults={"is_staff": True, "is_superuser": False},
    )
    if created or reset_password:
        user.set_password(password)
        user.save(update_fields=["password"])

    for profile_data in DEFAULT_PROFILES:
        profile, _ = Perfil.objects.update_or_create(
            slug=profile_data["slug"],
            defaults={
                "nome": profile_data["nome"],
                "ordem": profile_data["ordem"],
            },
        )

        valid_days = set(profile_data["dias_salario"])
        for due_day in valid_days:
            SalarioParcela.objects.get_or_create(
                perfil=profile,
                dia_recebimento=due_day,
                defaults={"valor": DEFAULT_SALARY_VALUE},
            )
        profile.parcelas_salariais.exclude(dia_recebimento__in=valid_days).delete()

    for nome, cor, icone in DEFAULT_CATEGORIES:
        Categoria.objects.update_or_create(
            nome=nome,
            defaults={"cor": cor, "icone": icone},
        )

    return {
        "user": user,
        "profiles": list_profiles(),
        "categories": Categoria.objects.order_by("nome"),
    }

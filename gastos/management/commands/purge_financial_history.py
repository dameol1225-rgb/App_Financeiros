from django.core.management.base import BaseCommand
from django.utils import timezone

from gastos.models import Parcela
from perfis.models import Perfil
from perfis.services import get_profile_history_anchor
from financeiro.utils import add_months


class Command(BaseCommand):
    help = "Remove gastos, parcelas e rendas extras quando um perfil completa 12 meses de historico."

    def handle(self, *args, **options):
        today = timezone.localdate()
        cleaned_profiles = 0
        deleted_gastos = 0
        deleted_parcelas = 0
        deleted_rendas = 0
        deleted_debitos = 0

        for profile in Perfil.objects.all():
            anchor = get_profile_history_anchor(profile)
            if not anchor:
                continue

            if add_months(anchor, 12) > today:
                continue

            parcelas_count = Parcela.objects.filter(gasto__perfil=profile).count()
            gastos_count = profile.gastos.count()
            rendas_count = profile.rendas_extras.count()
            debitos_count = profile.gastos_debito.count()

            profile.gastos.all().delete()
            profile.rendas_extras.all().delete()
            profile.gastos_debito.all().delete()

            cleaned_profiles += 1
            deleted_gastos += gastos_count
            deleted_parcelas += parcelas_count
            deleted_rendas += rendas_count
            deleted_debitos += debitos_count

        self.stdout.write(
            self.style.SUCCESS(
                "Limpeza concluida: "
                f"{cleaned_profiles} perfil(is), "
                f"{deleted_gastos} gasto(s), "
                f"{deleted_parcelas} parcela(s) e "
                f"{deleted_rendas} renda(s) extra(s) e "
                f"{deleted_debitos} compra(s) no debito removidos."
            )
        )

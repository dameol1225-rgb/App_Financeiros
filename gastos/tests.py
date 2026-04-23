from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gastos.models import Categoria, Gasto, GastoDebito, Parcela
from gastos.services import create_gasto_for_profile, mark_next_installment_paid
from perfis.models import Perfil, RendaExtra
from perfis.services import ensure_default_setup


class FinanceFlowTests(TestCase):
    def setUp(self):
        ensure_default_setup(reset_password=True)
        self.samuel = Perfil.objects.get(slug="samuel-menezes")
        self.grazi = Perfil.objects.get(slug="grazi-xavier")
        self.alimentacao = Categoria.objects.get(nome="Alimentacao")
        self.transporte = Categoria.objects.get(nome="Transporte")

    def login_and_select(self, profile):
        self.client.post(
            reverse("login"),
            {
                "username": settings.CASAL_ORGANIZADO_USERNAME,
                "password": settings.CASAL_ORGANIZADO_PASSWORD,
            },
        )
        self.client.post(reverse("select_profile"), {"profile_slug": profile.slug})

    def test_installments_are_generated_across_month_boundaries(self):
        gasto = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Notebook",
                "valor_total": Decimal("300.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 30,
                "data_inicio": timezone.datetime(2026, 1, 31).date(),
            },
        )

        due_dates = list(gasto.parcelas.order_by("numero").values_list("data_vencimento", flat=True))

        self.assertEqual(
            due_dates,
            [
                timezone.datetime(2026, 2, 28).date(),
                timezone.datetime(2026, 3, 30).date(),
                timezone.datetime(2026, 4, 30).date(),
            ],
        )

    def test_dashboard_calculates_salary_expense_balance_and_extra_income(self):
        today = timezone.localdate().replace(day=1)
        salary_values = [Decimal("1000.00"), Decimal("500.00"), Decimal("300.00")]
        for parcela, value in zip(self.samuel.parcelas_salariais.order_by("dia_recebimento"), salary_values):
            parcela.valor = value
            parcela.save(update_fields=["valor"])

        RendaExtra.objects.create(
            perfil=self.samuel,
            descricao="Freelance",
            valor=Decimal("200.00"),
            data=today,
        )
        GastoDebito.objects.create(
            perfil=self.samuel,
            valor=Decimal("50.00"),
            data=today,
            observacao="Mercado no debito",
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Mercado",
                "valor_total": Decimal("120.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.context["salary_total"], Decimal("1800.00"))
        self.assertEqual(response.context["extra_total"], Decimal("200.00"))
        self.assertEqual(response.context["debit_total"], Decimal("50.00"))
        self.assertEqual(response.context["expense_total"], Decimal("110.00"))
        self.assertEqual(response.context["projected_balance"], Decimal("1890.00"))

    def test_debit_expense_is_saved_without_due_bucket(self):
        today = timezone.localdate()
        self.login_and_select(self.samuel)

        response = self.client.post(
            reverse("add_debit_expense"),
            {
                "debit-valor": "45.90",
                "debit-data": today.isoformat(),
                "debit-observacao": "Padaria",
            },
        )

        self.assertRedirects(response, reverse("gastos"))
        self.assertTrue(GastoDebito.objects.filter(perfil=self.samuel, observacao="Padaria").exists())

        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard_response.context["due_installments_count"], 0)
        self.assertContains(self.client.get(reverse("gastos")), "Padaria")

    def test_dashboard_due_filters_work_by_month_category_and_status(self):
        today = timezone.localdate().replace(day=1)
        gasto = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Mercado do mes",
                "valor_total": Decimal("120.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.transporte,
                "nome": "Transporte futuro",
                "valor_total": Decimal("200.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today + timedelta(days=32),
            },
        )
        mark_next_installment_paid(gasto)

        self.login_and_select(self.samuel)
        response = self.client.get(
            reverse("dashboard"),
            {
                "due_mes": today.month,
                "due_ano": today.year,
                "due_categoria": self.alimentacao.id,
                "due_status": Parcela.Status.PAGO,
            },
        )

        self.assertEqual(len(response.context["due_installments"]), 1)
        self.assertEqual(response.context["due_installments"][0].gasto.nome, "Mercado do mes")
        self.assertEqual(response.context["selected_due_status"], Parcela.Status.PAGO)
        due_buckets = {bucket["day"]: bucket for bucket in response.context["due_buckets"]}
        self.assertEqual(len(due_buckets[20]["items"]), 1)
        self.assertContains(response, "due-day-card")
        self.assertNotContains(response, "due-list-grid")

    def test_history_filters_category_and_status(self):
        today = timezone.localdate().replace(day=1)
        ativo = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Feira",
                "valor_total": Decimal("90.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        quitado = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.transporte,
                "nome": "Combustivel",
                "valor_total": Decimal("50.00"),
                "quantidade_parcelas": 1,
                "dia_vencimento": 5,
                "data_inicio": today,
            },
        )
        mark_next_installment_paid(quitado)

        self.login_and_select(self.samuel)
        response = self.client.get(
            reverse("historico"),
            {
                "mes": today.month,
                "ano": today.year,
                "categoria": self.alimentacao.id,
                "status": Gasto.Status.ATIVO,
            },
        )

        self.assertEqual(len(response.context["entries"]), 1)
        self.assertEqual(response.context["entries"][0]["gasto"].pk, ativo.pk)
        self.assertEqual(response.context["chart"]["labels"], ["Alimentacao"])

    def test_print_preview_is_scoped_to_active_profile(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Cartao Samuel",
                "valor_total": Decimal("150.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.grazi,
            {
                "categoria": self.transporte,
                "nome": "Cartao Grazi",
                "valor_total": Decimal("210.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 5,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("export_pdf"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cartao Samuel")
        self.assertNotContains(response, "Cartao Grazi")
        self.assertContains(response, "Imprimir / Salvar PDF")

    def test_edit_gasto_updates_database_and_preserves_paid_progress(self):
        today = timezone.localdate().replace(day=1)
        gasto = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Notebook",
                "valor_total": Decimal("300.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        mark_next_installment_paid(gasto)

        self.login_and_select(self.samuel)
        response = self.client.post(
            reverse("edit_gasto", args=[gasto.id]),
            {
                "nome": "Notebook editado",
                "valor_total": "400.00",
                "quantidade_parcelas": 4,
                "dia_vencimento": 30,
                "categoria": self.transporte.id,
                "data_inicio": today,
            },
        )

        gasto.refresh_from_db()
        self.assertRedirects(response, reverse("gastos"))
        self.assertEqual(gasto.nome, "Notebook editado")
        self.assertEqual(gasto.valor_total, Decimal("400.00"))
        self.assertEqual(gasto.quantidade_parcelas, 4)
        self.assertEqual(gasto.categoria, self.transporte)
        self.assertEqual(gasto.parcelas.count(), 4)
        self.assertEqual(gasto.parcelas.filter(status=Parcela.Status.PAGO).count(), 1)

    def test_delete_gasto_removes_record_from_database(self):
        today = timezone.localdate().replace(day=1)
        gasto = create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Conta removivel",
                "valor_total": Decimal("100.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.post(reverse("delete_gasto", args=[gasto.id]))

        self.assertRedirects(response, reverse("gastos"))
        self.assertFalse(Gasto.objects.filter(pk=gasto.id).exists())

    def test_add_gasto_form_offers_existing_names_as_suggestions(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Carro",
                "valor_total": Decimal("100.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("add_gasto"))

        self.assertContains(response, 'list="expense-name-options"')
        self.assertContains(response, 'data-expense-name-select')
        self.assertContains(response, '<option value="Carro">', html=True)

    def test_dashboard_groups_active_debts_by_name(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.transporte,
                "nome": "Carro",
                "valor_total": Decimal("120.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 5,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.transporte,
                "nome": "Carro",
                "valor_total": Decimal("180.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(len(response.context["debt_cards"]), 1)
        debt_card = response.context["debt_cards"][0]
        self.assertEqual(debt_card["nome"], "Carro")
        self.assertEqual(debt_card["entries_count"], 2)
        self.assertEqual(debt_card["installment_purchase_count"], 2)
        self.assertEqual(debt_card["remaining_count"], 5)
        self.assertEqual(debt_card["remaining_total"], Decimal("300.00"))

    def test_grouped_card_separates_single_payment_from_installments(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Cartão Mercado",
                "valor_total": Decimal("80.00"),
                "quantidade_parcelas": 1,
                "dia_vencimento": 5,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Cartão Mercado",
                "valor_total": Decimal("300.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("dashboard"))

        debt_card = response.context["debt_cards"][0]
        self.assertEqual(debt_card["entries_count"], 2)
        self.assertEqual(debt_card["single_payment_count"], 1)
        self.assertEqual(debt_card["installment_purchase_count"], 1)
        self.assertTrue(debt_card["single_payment_entries"][0]["is_single_payment"])
        self.assertContains(response, "Compras à vista")
        self.assertContains(response, "Parcelas deste cartão")

    def test_dashboard_groups_names_even_with_accent_variation(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Cartão Assaí",
                "valor_total": Decimal("100.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Cartao Assai",
                "valor_total": Decimal("90.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(len(response.context["debt_cards"]), 1)
        self.assertContains(response, "Cartão Assaí")

    def test_annual_expense_chart_respects_selected_year(self):
        current_year = timezone.localdate().year
        previous_year = current_year - 1

        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Ano atual",
                "valor_total": Decimal("120.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 5,
                "data_inicio": timezone.datetime(current_year, 1, 1).date(),
            },
        )
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.transporte,
                "nome": "Ano anterior",
                "valor_total": Decimal("300.00"),
                "quantidade_parcelas": 3,
                "dia_vencimento": 20,
                "data_inicio": timezone.datetime(previous_year, 1, 1).date(),
            },
        )

        self.login_and_select(self.samuel)
        response = self.client.get(reverse("dashboard"), {"annual_ano": previous_year})

        self.assertEqual(response.context["selected_annual_year"], previous_year)
        self.assertEqual(response.context["annual_expense_total"], Decimal("300.00"))
        self.assertEqual(response.context["annual_expense_chart"]["values"][0], 100.0)

    def test_purge_financial_history_removes_only_due_profiles(self):
        old_date = timezone.localdate() - timedelta(days=370)
        recent_date = timezone.localdate() - timedelta(days=20)

        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.alimentacao,
                "nome": "Conta antiga",
                "valor_total": Decimal("100.00"),
                "quantidade_parcelas": 1,
                "dia_vencimento": 5,
                "data_inicio": old_date,
            },
        )
        RendaExtra.objects.create(
            perfil=self.samuel,
            descricao="Extra antigo",
            valor=Decimal("50.00"),
            data=old_date,
        )
        GastoDebito.objects.create(
            perfil=self.samuel,
            valor=Decimal("35.00"),
            data=old_date,
            observacao="Cafe antigo",
        )
        create_gasto_for_profile(
            self.grazi,
            {
                "categoria": self.transporte,
                "nome": "Conta recente",
                "valor_total": Decimal("120.00"),
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": recent_date,
            },
        )

        call_command("purge_financial_history")

        self.assertFalse(self.samuel.gastos.exists())
        self.assertFalse(self.samuel.rendas_extras.exists())
        self.assertFalse(self.samuel.gastos_debito.exists())
        self.assertTrue(self.grazi.gastos.exists())

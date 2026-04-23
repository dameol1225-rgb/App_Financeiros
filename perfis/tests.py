from io import BytesIO

from datetime import timedelta

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from gastos.models import Categoria
from gastos.services import create_gasto_for_profile
from perfis.models import Perfil
from perfis.services import ensure_default_setup


class AuthAndProfileFlowTests(TestCase):
    def setUp(self):
        ensure_default_setup(reset_password=True)
        self.samuel = Perfil.objects.get(slug="samuel-menezes")
        self.grazi = Perfil.objects.get(slug="grazi-xavier")
        self.categoria = Categoria.objects.first()

    def login(self):
        return self.client.post(
            reverse("login"),
            {
                "username": settings.CASAL_ORGANIZADO_USERNAME,
                "password": settings.CASAL_ORGANIZADO_PASSWORD,
            },
        )

    def select_profile(self, profile):
        self.client.post(reverse("select_profile"), {"profile_slug": profile.slug})

    def test_seeded_credentials_allow_login(self):
        response = self.login()

        self.assertRedirects(response, reverse("select_profile"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_invalid_password_does_not_authenticate(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": settings.CASAL_ORGANIZADO_USERNAME,
                "password": "senha-invalida",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response.context["form"].errors)

    def test_profile_selection_keeps_data_isolated(self):
        today = timezone.localdate().replace(day=1)
        create_gasto_for_profile(
            self.samuel,
            {
                "categoria": self.categoria,
                "nome": "Cartao Samuel",
                "valor_total": "120.00",
                "quantidade_parcelas": 2,
                "dia_vencimento": 20,
                "data_inicio": today,
            },
        )
        create_gasto_for_profile(
            self.grazi,
            {
                "categoria": self.categoria,
                "nome": "Cartao Grazi",
                "valor_total": "90.00",
                "quantidade_parcelas": 3,
                "dia_vencimento": 5,
                "data_inicio": today,
            },
        )

        self.login()
        self.select_profile(self.samuel)
        response = self.client.get(reverse("gastos"))

        self.assertContains(response, "Cartao Samuel")
        self.assertNotContains(response, "Cartao Grazi")

    def test_selected_theme_is_persisted_per_profile(self):
        self.login()
        self.select_profile(self.samuel)

        self.client.post(
            reverse("update_theme"),
            {
                "theme": "black",
                "next": reverse("dashboard"),
            },
        )

        self.samuel.refresh_from_db()
        self.assertEqual(self.samuel.tema, "black")

        self.client.post(reverse("select_profile"), {"profile_slug": self.samuel.slug})
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "theme-black")

    def test_extra_sections_visibility_is_persisted_per_profile(self):
        self.login()
        self.select_profile(self.samuel)

        self.client.post(
            reverse("toggle_extra_sections"),
            {
                "mostrar_funcoes_extras": "0",
                "next": reverse("dashboard"),
            },
        )

        self.samuel.refresh_from_db()
        self.assertFalse(self.samuel.mostrar_funcoes_extras)

        response = self.client.get(reverse("dashboard"))

        self.assertNotContains(response, "Recebimentos fixos")
        self.assertNotContains(response, "Adicionar renda extra")

    def test_profile_image_is_saved_in_database(self):
        self.login()
        self.select_profile(self.samuel)

        image_stream = BytesIO()
        Image.new("RGB", (64, 64), "#2563eb").save(image_stream, format="PNG")
        image_stream.seek(0)

        response = self.client.post(
            reverse("update_profile_image"),
            {
                "next": reverse("dashboard"),
                "image": SimpleUploadedFile(
                    "avatar.png",
                    image_stream.getvalue(),
                    content_type="image/png",
                ),
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.samuel.refresh_from_db()
        self.assertTrue(self.samuel.foto_perfil.startswith("data:image/webp;base64,"))

        profile_page = self.client.get(reverse("select_profile"))
        self.assertContains(profile_page, "data:image/webp;base64,")

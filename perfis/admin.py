from django.contrib import admin

from perfis.models import Perfil, RendaExtra, SalarioParcela


class SalarioParcelaInline(admin.TabularInline):
    model = SalarioParcela
    extra = 0


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ordem")
    ordering = ("ordem", "nome")
    inlines = [SalarioParcelaInline]


@admin.register(RendaExtra)
class RendaExtraAdmin(admin.ModelAdmin):
    list_display = ("descricao", "perfil", "valor", "data")
    list_filter = ("perfil", "data")


@admin.register(SalarioParcela)
class SalarioParcelaAdmin(admin.ModelAdmin):
    list_display = ("perfil", "dia_recebimento", "valor")
    list_filter = ("perfil", "dia_recebimento")

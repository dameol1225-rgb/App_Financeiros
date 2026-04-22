from django.contrib import admin

from gastos.models import Categoria, Gasto, Parcela


class ParcelaInline(admin.TabularInline):
    model = Parcela
    extra = 0
    readonly_fields = ("numero", "valor", "data_vencimento")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cor", "icone")


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("nome", "perfil", "categoria", "valor_total", "quantidade_parcelas", "status")
    list_filter = ("perfil", "categoria", "status", "dia_vencimento")
    search_fields = ("nome",)
    inlines = [ParcelaInline]


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ("gasto", "numero", "valor", "data_vencimento", "status")
    list_filter = ("status", "data_vencimento")

from django.urls import path

from gastos import views


urlpatterns = [
    path("gastos/", views.gastos_list, name="gastos"),
    path("gastos/novo/", views.add_gasto, name="add_gasto"),
    path("gastos/<int:gasto_id>/editar/", views.edit_gasto, name="edit_gasto"),
    path("gastos/<int:gasto_id>/remover/", views.delete_gasto, name="delete_gasto"),
    path("gastos/<int:gasto_id>/marcar-pagamento/", views.mark_next_payment, name="mark_next_payment"),
    path("gastos/<int:gasto_id>/desfazer-pagamento/", views.undo_payment, name="undo_payment"),
    path("historico/", views.historico, name="historico"),
    path("exportar/pdf/", views.export_pdf, name="export_pdf"),
]


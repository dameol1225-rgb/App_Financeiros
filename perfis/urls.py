from django.urls import path

from perfis import views


urlpatterns = [
    path("", views.login_view, name="login"),
    path("selecionar-perfil/", views.select_profile, name="select_profile"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("renda-extra/", views.extra_income_page, name="extra_income_page"),
    path("perfil/", views.profile_settings, name="profile_settings"),
    path("mais/", views.more_menu, name="more_menu"),
    path("tema/", views.update_theme, name="update_theme"),
    path("preferencias/funcoes-extras/", views.toggle_extra_sections, name="toggle_extra_sections"),
    path("preferencias/foto/", views.update_profile_image, name="update_profile_image"),
    path("preferencias/foto/remover/", views.remove_profile_image, name="remove_profile_image"),
    path("dashboard/salarios/", views.update_salary, name="update_salary"),
    path("dashboard/renda-extra/", views.add_extra_income, name="add_extra_income"),
    path("dashboard/renda-extra/<int:extra_income_id>/editar/", views.edit_extra_income, name="edit_extra_income"),
    path("dashboard/renda-extra/<int:extra_income_id>/excluir/", views.delete_extra_income, name="delete_extra_income"),
    path("logout/", views.logout_view, name="logout"),
]

from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


app_name = "ui"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="ui/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="ui:login"), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("fila/", views.fila, name="fila"),
    path("arquivos/<int:arquivo_id>/download/", views.download_arquivo, name="download_arquivo"),
    path("recebimento/", views.recebimento, name="recebimento"),
    path("planilhas/", views.planilhas, name="planilhas"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("diagnostico/", views.diagnostico, name="diagnostico"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("sobre/", views.sobre, name="sobre"),
]

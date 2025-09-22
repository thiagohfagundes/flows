from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.register_view, name="registro"),
    path("perfil/", views.perfil, name="perfil_usuario"),

    # onboarding (nomes únicos)
    path("onboarding/perfil/", views.PerfilView.as_view(), name="onboarding_perfil"),
    path("onboarding/empresa/", views.EmpresaView.as_view(), name="onboarding_empresa"),
    path("onboarding/integracao/", views.IntegracaoView.as_view(), name="onboarding_integracao"),
    path("onboarding/processo/", views.PrimeiroProcessoView.as_view(), name="onboarding_processo"),
    path("onboarding/resumo/", views.ResumoView.as_view(), name="onboarding_resumo"),
    path("onboarding/processo/escolha/", views.ProcessChoiceView.as_view(), name="onboarding_process_choice"),
]
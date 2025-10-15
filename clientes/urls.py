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

    # empresa
    path('empresa/<int:pk>/', views.empresa_settings, name='empresa_settings'),

    # endpoints HTMX (partials)
    path('empresa/<int:pk>/info/', views.empresa_info_partial, name='empresa_info_partial'),
    path('empresa/<int:pk>/info/edit/', views.empresa_info_partial, name='empresa_info_edit'),  # same view handles GET/POST edit with HTMX
    path('empresa/<int:pk>/colaboradores/', views.empresa_colaboradores_partial, name='empresa_colaboradores_partial'),
    path('empresa/<int:pk>/licencas/', views.empresa_licencas_partial, name='empresa_licencas_partial'),

    path('empresa/<int:pk>/colaboradores/', views.empresa_colaboradores_partial, name='empresa_colaboradores_partial'),
    path('empresa/<int:pk>/colaboradores/<int:pessoa_pk>/remove/', views.empresa_remove_colaborador, name='empresa_remove_colaborador'),
    path('empresa/<int:pk>/colaboradores/<int:pessoa_pk>/edit/', views.empresa_edit_colaborador, name='empresa_edit_colaborador'),
    path('empresa/<int:pk>/colaboradores/<int:pessoa_pk>/permissoes/', views.empresa_colaborador_permissoes, name='empresa_colaborador_permissoes'),

    path('empresa/<int:pk>/colaboradores/<int:pessoa_pk>/confirm_remove/', views.empresa_remove_colaborador_confirm, name='empresa_remove_colaborador_confirm'),
]
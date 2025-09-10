from django.urls import path
from . import views

urlpatterns = [
    path("importar/contratos/", views.importar_contratos_meus, name="importar_contratos"),
    path("importar/proprietarios/", views.importar_proprietarios, name="importar_proprietarios"),
    path("contratos/<int:pk>/", views.contrato_detail, name="contrato_detail"),
]
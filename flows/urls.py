from django.contrib import admin
from django.urls import path, include
from importador_erp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kanban.urls')),
    path('usuarios/', include('clientes.urls')),
    path("kanban-templates/", include("kanban_templates.urls")),
    path('integrador/', include('integrador.urls')),
    path('importador/', include('importador_erp.urls')),
    path('meus-clientes/', views.MeusClientesListView.as_view(), name='meus_clientes'),
    path("meus-contratos/", views.ContratosLocacaoListView.as_view(), name="meus_contratos"),
    path('dashboard/', include('dashboards.urls')),
]
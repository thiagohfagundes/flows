from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kanban.urls')),
    path('usuarios/', include('clientes.urls')),
    path("kanban-templates/", include("kanban_templates.urls")),
    path('integrador/', include('integrador.urls')),
    path('importador/', include('importador_erp.urls')),
]
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('kanban/', include('kanban.urls')),
    path('usuarios/', include('clientes.urls')),
]
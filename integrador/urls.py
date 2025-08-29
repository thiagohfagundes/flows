from django.urls import path
from . import views

app_name = 'integrador'

urlpatterns = [
    path('conectar/licenca/<int:license_id>/', views.iniciar_autorizacao, name='start_license'),   # se você também mantiver o fluxo OAuth
    path('callback/', views.callback_autorizacao, name='callback'),
    path('verificar/licenca/<int:license_id>/', views.verificar_conexao_view, name='verificar_license'),

    # <<< NOVAS >>>
    path('token/licenca/<int:license_id>/', views.definir_access_token, name='definir_token'),
    path('desconectar/licenca/<int:license_id>/', views.desconectar_license, name='desconectar_license'),
]
# kanban/urls.py
from django.urls import path
from . import views

app_name = "kanban"

urlpatterns = [
    # navegação principal
    path("", views.home, name="home"),
    path("pipelines/", views.pipeline_list, name="pipeline_list"),
    path("pipelines/<int:pipeline_id>/", views.pipeline_detail, name="pipeline_detail"),

    # etapas (criar/editar rápido pela UI)
    path("pipelines/<int:pipeline_id>/etapas/new/", views.etapa_create, name="etapa_create"),
    path("etapas/<int:etapa_id>/edit/", views.etapa_edit, name="etapa_edit"),

    # cards (CRUD rápido + mover)
    path("pipelines/<int:pipeline_id>/cards/new/", views.card_create, name="card_create"),
    path("cards/<int:card_id>/edit/", views.card_edit, name="card_edit"),
    path("cards/<int:card_id>/delete/", views.card_delete, name="card_delete"),
    path("cards/<int:card_id>/move/", views.card_move, name="card_move"),

    # tarefas (extra opcional)
    path("cards/<int:card_id>/tarefas/new/", views.tarefa_create, name="tarefa_create"),
    path("tarefas/<int:tarefa_id>/toggle/", views.tarefa_toggle, name="tarefa_toggle"),
]

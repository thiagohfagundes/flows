# kanban/urls.py
from django.urls import path
from . import views

app_name = "kanban"

urlpatterns = [
    # navegação principal
    path("", views.home, name="home"),
    path("pipelines/", views.pipeline_list, name="pipelines"),
    path("pipelines/<int:pipeline_id>/", views.pipeline_detail, name="pipeline_detail"),
    path("pipelines/detail/<int:pipeline_id>/", views.pipeline_detail, name="pipeline_details_view"), # MUDAR
    path("pipelines/config/<int:pipeline_id>/", views.pipeline_detail, name="pipeline_config_view"), # MUDAR
    path("pipelines/criar/stage-row/", views.pipeline_create_stage_row, name="pipeline_create_stage_row"),
    path("pipelines/criar/", views.pipeline_create, name="pipeline_create"), 
    path("pipelines/<int:pipeline_id>/delete/", views.pipeline_delete, name="pipeline_delete"),

    # etapas (criar/editar rápido pela UI)
    path("pipelines/<int:pipeline_id>/etapas/new/", views.etapa_create, name="etapa_create"),
    path("etapas/<int:etapa_id>/edit/", views.etapa_edit, name="etapa_edit"),
    path("pipelines/<int:pk>/editar/", views.pipeline_edit, name="pipeline_edit"),
    path("pipelines/<int:pk>/excluir/", views.pipeline_delete, name="pipeline_delete"),

    # cards (CRUD rápido + mover)
    path("pipelines/<int:pipeline_id>/cards/new/", views.card_create, name="card_create"),
    path("cards/<int:card_id>/edit/", views.card_edit, name="card_edit"),
    path("cards/<int:card_id>/delete/", views.card_delete, name="card_delete"),
    path("cards/<int:card_id>/move/", views.card_move, name="card_move"),
    path("cards/<int:card_id>/", views.card_detail, name="card_detail"),

    # tarefas (extra opcional)
    path("cards/<int:card_id>/tarefas/new/", views.tarefa_create, name="tarefa_create"),
    path("tarefas/<int:tarefa_id>/toggle/", views.tarefa_toggle, name="tarefa_toggle"),

    #propriedades
    path("cards/<int:card_id>/props/", views.card_props_update, name="card_props_update"),
    path("pipelines/create/prop-row/", views.pipeline_create_prop_row, name="pipeline_create_prop_row"),

    # checklists
    path("pipelines/<int:pipeline_id>/checklists/novo/", views.checklist_create_in_pipeline, name="checklist_create_in_pipeline"),
    path("checklists/item-empty/", views.checklist_item_empty_row, name="checklist_item_vazio"),

    # comentários
    path("cards/<int:card_id>/comentarios/novo/", views.comentario_create, name="comentario_create"),

    # Busca (GET, retorna lista parcial)
    path("cards/<int:card_id>/buscar-clientes/", views.card_buscar_clientes, name="card_buscar_clientes"),
    path("cards/<int:card_id>/buscar-contratos/", views.card_buscar_contratos, name="card_buscar_contratos"),

    # Adição/remoção (POST) de vínculos
    path("cards/<int:card_id>/add-cliente/<int:cliente_id>/", views.card_add_cliente, name="card_add_cliente"),
    path("cards/<int:card_id>/rm-cliente/<int:cliente_id>/", views.card_rm_cliente, name="card_rm_cliente"),
    path("cards/<int:card_id>/add-contrato/<int:contrato_id>/", views.card_add_contrato, name="card_add_contrato"),
    path("cards/<int:card_id>/rm-contrato/<int:contrato_id>/", views.card_rm_contrato, name="card_rm_contrato"),
]

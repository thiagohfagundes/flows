# kanban_templates/urls.py
from django.urls import path
from . import views

app_name = "kanban_templates"

urlpatterns = [
    path("templates/from-pipeline/<int:pipeline_id>/", views.template_from_pipeline, name="template_from_pipeline"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/<int:tpl_id>/", views.template_detail, name="template_detail"),
]

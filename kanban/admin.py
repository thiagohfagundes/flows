from django.contrib import admin
from .models import Etapa, Pipeline, Card, Tarefa, Propriedade

# Register your models here.
admin.site.register(Etapa)
admin.site.register(Pipeline)
admin.site.register(Card)
admin.site.register(Tarefa)
admin.site.register(Propriedade)


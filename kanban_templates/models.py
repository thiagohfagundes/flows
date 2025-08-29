from django.db import models
from django.contrib.auth.models import User

VISIBILIDADE = (("private","Privado"), ("org","Organização"), ("public","Público"))

class PipelineTemplate(models.Model):
    nome         = models.CharField(max_length=120)
    descricao    = models.TextField(blank=True, null=True)
    doc          = models.JSONField(blank=True, null=True)  # ← JSON com tudo
    visibilidade = models.CharField(max_length=10, choices=VISIBILIDADE, default="private")
    criado_por   = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
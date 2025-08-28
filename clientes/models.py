from django.db import models
from django.contrib.auth.models import User

# Create your models here.
TIPO_CLIENTE = (
    ("IMOBILIARIA", "Imobiliária"),
    ("CLIENTE_FINAL", "Cliente Final"),
    ("OUTRO", "Outro")
)

class Pessoa(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)       # pode usar o do User
    cargo = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pessoa')

    # 👇 complementos
    biografia = models.TextField(blank=True, null=True)
    data_nascimento = models.DateField(null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    website_url = models.URLField(null=True, blank=True)
    recebe_emails = models.BooleanField(default=True)

    def __str__(self):
        return self.nome or self.usuario.get_username()

class Empresa(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CLIENTE, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_ult_modificacao = models.DateTimeField(auto_now=True)
    responsavel = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='responsavel')
    colaboradores = models.ManyToManyField(Pessoa, related_name='empresa')

    def __str__(self):
        return self.nome

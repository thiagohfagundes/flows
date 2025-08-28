from time import timezone
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
STATUS_ETAPA = (
    ('ABERTO', 'Aberto'),
    ('PERDIDO', 'Perdido'),
    ('CONCLUIDO', 'Concluído'),
)

TIPOS_PROPRIEDADE = (
    ('TEXTO', 'Texto'),
    ('NUMERO', 'Número'),
    ('BOOLEANO', 'Booleano'),
    ('CATEGORICO', 'Categórico'),
    ('DATA', 'Data'),
)

STATUS_TAREFA = (
    ('ABERTO', 'Aberto'),
    ('EM_ANDAMENTO', 'Em Andamento'),
    ('CONCLUIDO', 'Concluído'),
    ('CANCELADO', 'Cancelado'),
    ('PENDENTE', 'Pendente'),
    ('AGUARDANDO_APROVACAO', 'Aguardando Aprovação'),
    ('ATRASADA', 'Atrasada')
)

class Etapa(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    posicao = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_ETAPA, default='ABERTO')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_ult_modificacao = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome
    
class Pipeline(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    etapas = models.ManyToManyField(Etapa, related_name='pipelines', blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_ult_modificacao = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome

class Card(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='tickets')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_ult_modificacao = models.DateTimeField(auto_now=True)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='cards', blank=True, null=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    atribuido_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards_atribuidos', blank=True, null=True)

    def __str__(self):
        return self.titulo
    
    def mover_para_etapa(self, nova_etapa):
        self.etapa = nova_etapa
        self.save()

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

class Propriedade(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100, choices=TIPOS_PROPRIEDADE)
    valor = models.TextField(blank=True, null=True)
    card = models.ForeignKey('Card', on_delete=models.CASCADE, related_name='propriedades')
    categoria = models.ForeignKey('Categoria', on_delete=models.CASCADE, related_name='propriedades', blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.tipo})"

class Tarefa(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    concluido = models.BooleanField(default=False)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='tarefas')
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='tarefas', blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)
    data_ult_modificacao = models.DateTimeField(auto_now=True)
    prazo = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_TAREFA, default='ABERTO')
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    atribuido_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas_atribuidas', blank=True, null=True)

    def __str__(self):
        return self.titulo

    def concluir(self):
        self.concluido = True
        self.data_conclusao = timezone.now()
        self.save()

    def atrasar(self):
        self.status = 'ATRASADA'
        self.save()

    def reabrir(self):
        self.status = 'ABERTO'
        self.save()
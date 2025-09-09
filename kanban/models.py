from time import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from importador_erp.models import Cliente, ContratoLocacao

# Create your models here.
STATUS_ETAPA = (
    ('ABERTO', 'Aberto'),
    ('PERDIDO', 'Perdido'),
    ('CONCLUIDO', 'Concluído'),
)

TIPOS_PROPRIEDADE = [
    ("text", "Texto"),
    ("number", "Número"),
    ("bool", "Booleano"),
    ("date", "Data"),
    ("select", "Seleção"),
]

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
    clientes_associados = models.ManyToManyField(Cliente, blank=True, related_name='cards')
    contratos_locacao = models.ManyToManyField(ContratoLocacao, blank=True, related_name='cards')

    def __str__(self):
        return self.titulo
    
    def mover_para_etapa(self, nova_etapa):
        self.etapa = nova_etapa
        self.save()

    def tarefas_total(self):
        return self.tarefas.count()

    def tarefas_concluidas(self):
        return self.tarefas.filter(concluido=True).count()

    
class PipelinePropriedade(models.Model):
    pipeline   = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="propriedades_def")
    nome       = models.CharField(max_length=100)
    tipo       = models.CharField(max_length=100, choices=TIPOS_PROPRIEDADE)
    obrigatorio= models.BooleanField(default=False)
    ordem      = models.PositiveIntegerField(default=0)
    opcoes      = models.JSONField(blank=True, null=True)
    valor_padrao = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("pipeline", "nome")
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.pipeline.nome} · {self.nome}"

class Propriedade(models.Model):
    card       = models.ForeignKey('Card', on_delete=models.CASCADE, related_name='propriedades')
    definicao  = models.ForeignKey('PipelinePropriedade', on_delete=models.CASCADE, related_name='instancias', blank=True, null=True)
    valor      = models.TextField(blank=True, null=True)
    nome = models.CharField(max_length=100, blank=True, null=True)
    tipo = models.CharField(max_length=100, choices=TIPOS_PROPRIEDADE, blank=True, null=True)

    def __str__(self):
        return f"{self.definicao.nome} = {self.valor}"

class Checklist(models.Model):
    nome        = models.CharField(max_length=120)
    descricao   = models.TextField(blank=True, null=True)
    pipeline    = models.ForeignKey('Pipeline', on_delete=models.CASCADE, related_name='checklists', null=True, blank=True)
    ordem       = models.PositiveIntegerField(default=0)
    criado_por  = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.nome} → {self.pipeline}"

class ChecklistItem(models.Model):
    checklist   = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='itens')
    titulo      = models.CharField(max_length=200)
    descricao   = models.TextField(blank=True, null=True)
    obrigatorio = models.BooleanField(default=False)
    ordem       = models.PositiveIntegerField(default=0)
    vinculado_a_etapa       = models.ForeignKey('Etapa', on_delete=models.CASCADE, related_name='checklists', null=True, blank=True)
    # Campos extras úteis:
    prazo_dias  = models.IntegerField(blank=True, null=True)   # prazo relativo ao nascimento do card
    atribuido_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_checklist_atribuidos')
    depende_de = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependentes')
    requer_aprovacao = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.titulo
    
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
    checklist_item = models.ForeignKey('ChecklistItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='tarefas_geradas')

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

class Comentario(models.Model):
    conteudo = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='comentarios')

    def __str__(self):
        return f"Comentário por {self.criado_por} em {self.criado_em}"
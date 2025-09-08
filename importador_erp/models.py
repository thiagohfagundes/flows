from django.db import models
from datetime import datetime
from .constantes import TIPOS_CLIENTE_LOCACAO
from clientes.models import ClienteLicense

# Create your models here.
class Cliente(models.Model):
    identificador_pessoa = models.IntegerField(unique=True)  # ID do cliente no Superlógica
    cpf_cnpj = models.CharField(max_length=20)
    rg = models.CharField(max_length=20)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino'), ('I', 'Indefinido')])
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=15)
    tipo = models.CharField(max_length=20, choices=TIPOS_CLIENTE_LOCACAO)

    def __str__(self):
        return self.nome
    
class ContratoLocacao(models.Model):
    identificador_contrato = models.IntegerField(unique=True)  # ID do contrato no Superlógica
    nome_do_imovel = models.CharField(max_length=100)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    aluguel_garantido = models.BooleanField(default=False)
    tipo_garantia = models.CharField(max_length=100)
    data_inicio_garantia = models.DateField(null=True, blank=True)
    data_fim_garantia = models.DateField(null=True, blank=True)
    data_inicio_seguro_incendio = models.DateField(null=True, blank=True)
    data_fim_seguro_incendio = models.DateField(null=True, blank=True)
    data_ultimo_reajuste = models.DateField(null=True, blank=True)
    valor_aluguel = models.DecimalField(max_digits=10, decimal_places=2)
    taxa_administracao = models.DecimalField(max_digits=7, decimal_places=2)
    taxa_locacao = models.DecimalField(max_digits=7, decimal_places=2)
    valor_venda_imovel = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    valor_garantia_parcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_seguro_incendio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tipo_imovel = models.CharField(max_length=100)
    tipo_contrato = models.CharField(max_length=100)
    status_contrato = models.CharField(max_length=100)
    contrato_ativo = models.BooleanField(default=True)
    renovacao_automatica = models.BooleanField(default=False)
    proprietarios = models.ManyToManyField(Cliente, related_name='contratos_proprietario')
    inquilinos = models.ManyToManyField(Cliente, related_name='contratos_inquilino')
    licenca = models.ForeignKey(ClienteLicense, on_delete=models.CASCADE, related_name='contratos')

    def __str__(self):
        return f"Contrato {self.id} - {self.proprietarios.first().nome}"

    def numero_inquilinos(self):
        return self.inquilinos.count()
    
    def numero_proprietarios(self):
        return self.proprietarios.count()
    
    def conferir_status(self):
        hoje = datetime.now().date()
        if self.data_fim < hoje:
            self.status_contrato = "Vencido"
        elif self.data_inicio >= hoje:
            self.status_contrato = "Vigente"
        self.save()

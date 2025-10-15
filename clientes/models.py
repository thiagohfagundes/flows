from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
        return self.nome or f"Empresa #{self.pk}"

class ClienteLicense(models.Model):
    """
    Uma licença do Superlógica Imobi associada a um cliente.
    O license_name é o subdomínio (ex: "minhaimobiliaria").
    """
    cliente = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='licencas')
    license_name = models.SlugField(unique=True)  # geralmente é globalmente único
    apelido = models.CharField(max_length=120, blank=True, help_text="apelido opcional para exibir na UI", null=True)

    class Meta:
        verbose_name = "Licença do Cliente"
        verbose_name_plural = "Licenças do Cliente"

    def __str__(self):
        return f"{self.license_name} ({self.cliente})"

class OnboardingStep(models.TextChoices):
    PERFIL = "perfil", "Perfil"
    EMPRESA = "empresa", "Empresa"
    INTEGRACAO = "integracao", "Integração"
    PROCESSO = "processo", "Primeiro Processo"
    RESUMO = "resumo", "Resumo"

class OnboardingState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="onboarding")
    current_step = models.CharField(max_length=20, choices=OnboardingStep.choices, default=OnboardingStep.PERFIL)
    onboarding_started_at = models.DateTimeField(default=timezone.now)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    def is_completed(self):
        return self.onboarding_completed_at is not None

    def advance(self, next_step: str):
        self.current_step = next_step
        self.save(update_fields=["current_step"])

    def complete(self):
        self.onboarding_completed_at = timezone.now()
        self.save(update_fields=["onboarding_completed_at"])
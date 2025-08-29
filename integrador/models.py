from django.db import models
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

# Create your models here.
def _get_fernet():
    key = settings.INTEGRADOR_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)

class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        f = _get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except InvalidToken:
            # Se a chave mudou e você precisa migrar, capture aqui.
            return None

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        f = _get_fernet()
        return f.encrypt(str(value).encode()).decode()

class LicenseIntegration(models.Model):
    license = models.OneToOneField('clientes.ClienteLicense', null=True, blank=True, on_delete=models.CASCADE, related_name='integracao')
    access_token = EncryptedTextField(blank=True, null=True)
    connected_at = models.DateTimeField(blank=True, null=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Integração de Licença"
        verbose_name_plural = "Integrações de Licenças"

    def __str__(self):
        return f"{self.license_name} (ativo={self.is_active})"
from django.contrib import admin
from .models import Pessoa, Empresa, ClienteLicense

# Register your models here.
admin.site.register(Pessoa)
admin.site.register(Empresa)
admin.site.register(ClienteLicense)

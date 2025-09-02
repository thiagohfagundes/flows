# integrador/views.py
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from clientes.models import ClienteLicense
from integrador.models import LicenseIntegration
import requests
from django.conf import settings
from .ingest import salvar_contratos, salvar_proprietarios


@login_required
def importar_contratos_meus(request):
    pessoa = getattr(request.user, "pessoa", None)
    if not pessoa:
        return HttpResponseBadRequest("Usuário sem Pessoa vinculada")
    licencas = pessoa.licencas.all()

    if not licencas:
        return HttpResponseNotFound("Usuário sem Licença vinculada")
    else:
        integ = LicenseIntegration.objects.get(license_id=licencas[0].id, is_active=True)
        token = integ.access_token
        print(token)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "app_token": settings.INTEGRADOR_APP_TOKEN,   # do .env
            "access_token": token,      # do banco (decrypt automático)
        }

        todos_contratos = []
        pagina = 1

        while True:
            url = f"http://apps.superlogica.net/imobiliaria/api/contratos?pagina={pagina}&itensPorPagina=50"
            response = requests.get(url, headers=headers).json()

            if response['data'] != []:
                todos_contratos.extend(response['data'])
                pagina += 1
            else:
                break

        salvar_contratos(todos_contratos, licencas[0])

    return JsonResponse({"licencas": [licenca.license_name for licenca in licencas], "contratos": todos_contratos})

def importar_proprietarios(request):
    pessoa = getattr(request.user, "pessoa", None)
    if not pessoa:
        return HttpResponseBadRequest("Usuário sem Pessoa vinculada")

    lic = pessoa.licencas.select_related("integracao").first()
    if not lic or not getattr(lic, "integracao", None) or not lic.integracao.is_active:
        return HttpResponseNotFound("Licença sem integração ativa")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "app_token": settings.INTEGRADOR_APP_TOKEN,
        "access_token": lic.integracao.access_token,  # já vem descriptografado
    }

    todos = []
    pagina = 1
    base = settings.IMOBILIARIAS_BASE_URL  # ex.: "https://apps.superlogica.net/imobiliaria/api"
    while True:
            url = f"http://apps.superlogica.net/imobiliaria/api/contratos?pagina={pagina}&itensPorPagina=50"
            response = requests.get(url, headers=headers).json()

            if response['data'] != []:
                todos.extend(response['data'])
                pagina += 1
            else:
                break
    
    print(todos)
    proprietarios = salvar_proprietarios(todos)
    return JsonResponse({"ok": True, "license_name": lic.license_name, "importados": len(proprietarios)})
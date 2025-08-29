from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages

from integrador.models import LicenseIntegration
from clientes.models import ClienteLicense
from .services import SuperlogicaClient

# tentar usar o helper de state, se você tiver criado conforme o blueprint
try:
    from .utils import read_state  # opcional
except Exception:
    read_state = None

@require_GET
def iniciar_autorizacao(request, license_name: str):
    # guardamos um fallback na sessão (caso o state se perca)
    request.session['integrador_license'] = license_name

    client = SuperlogicaClient(license_name)
    # se você chamar /integrador/conectar/<license_name>/?next=/clientes/42/
    # o build_authorization_url já embala esse "next" no state.
    url = client.build_authorization_url(request)
    return HttpResponseRedirect(url)

@require_GET
def callback_autorizacao(request):
    code = request.GET.get('code')
    if not code:
        return HttpResponseBadRequest('code ausente na URL de callback')

    license_name = None
    next_url = request.GET.get('next')  # raramente o provedor devolve; usamos o do state

    # 1) tentar pelo state (recomendado)
    state = request.GET.get('state')
    if state:
        try:
            payload = read_state(state)
            license_name = payload.get('license') or payload.get('licenca')
            next_url = payload.get('next') or next_url
        except Exception:
            pass

    # 2) fallbacks
    license_name = (
        license_name
        or request.GET.get('license')
        or request.GET.get('licenca')
        or request.session.get('integrador_license')
    )

    if not license_name:
        return HttpResponseBadRequest(
            'não foi possível determinar a license (use state assinado, ?license= ou sessão)'
        )

    client = SuperlogicaClient(license_name)

    try:
        access_token = client.exchange_code_for_access_token(code)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'falha na troca do code por access_token: {e}'}, status=400)

    client.save_access_token(license_name, access_token)
    try:
        messages.success(request, f'Integração com {license_name} concluída.')
    except Exception:
        pass

    return HttpResponseRedirect(next_url or '/')

@require_GET
def verificar_conexao_view(request, license_name: str):
    client = SuperlogicaClient(license_name)
    ok, payload = client.verificar_conexao()
    return JsonResponse({'ok': ok, 'data': payload}, status=200 if ok else 400)


@require_POST
def definir_access_token(request, license_id: int):
    lic = get_object_or_404(ClienteLicense, id=license_id)
    token = (request.POST.get("access_token") or "").strip()
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    if not token:
        messages.error(request, "Cole um access_token válido.")
        return redirect(next_url)

    try:
        client = SuperlogicaClient(lic)
        client.save_access_token(token)
    except Exception as e:
        messages.error(request, f"Erro ao salvar token: {e}")
        return redirect(next_url)

    # testa a conexão logo após salvar
    ok, payload = client.verificar_conexao()
    if ok:
        messages.success(request, f"Token salvo e conexão OK para {lic.license_name}.")
    else:
        # não falha o fluxo; só informa que precisa conferir
        msg = payload.get("error") if isinstance(payload, dict) else str(payload)
        messages.warning(request, f"Token salvo, mas verificação falhou: {msg}")

    return redirect(next_url)


# --- desconectar (apaga token e desativa) ---
@require_POST
def desconectar_license(request, license_id: int):
    lic = get_object_or_404(ClienteLicense, id=license_id)
    integ = LicenseIntegration.objects.filter(license=lic).first()
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if integ:
        integ.access_token = None
        integ.is_active = False
        integ.save(update_fields=["access_token", "is_active"])
        messages.info(request, f"Licença {lic.license_name} desconectada.")
    else:
        messages.info(request, "Esta licença já está desconectada.")
    return redirect(next_url)


# --- verificar conexão (JSON) ---
@require_GET
def verificar_conexao_view(request, license_id: int):
    lic = get_object_or_404(ClienteLicense, id=license_id)
    ok, payload = SuperlogicaClient(lic).verificar_conexao()
    return JsonResponse({"ok": ok, "data": payload}, status=200 if ok else 400)
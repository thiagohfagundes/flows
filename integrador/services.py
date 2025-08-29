# integrador/services/superlogica.py
import base64
import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from integrador.models import LicenseIntegration
from clientes.models import ClienteLicense  # import absoluto

logger = logging.getLogger(__name__)


class SuperlogicaClient:
    def __init__(self, cliente_license: ClienteLicense):
        self.lic = cliente_license
        self.license_name = cliente_license.license_name
        self.api_base = settings.SUPERLOGICA_API_BASE.rstrip("/")
        self.login_url_template = settings.URL_PARA_APP_TOKEN
        self.app_token = settings.INTEGRADOR_APP_TOKEN
        self.app_secret = settings.INTEGRADOR_APP_SECRET

    def build_authorization_url(self, request, next_url: str | None = None) -> str:
        from integrador.utils import make_state
        redirect_uri = request.build_absolute_uri(reverse("integrador:callback"))
        login_base = self.login_url_template.format(license=self.license_name)
        state_payload = {"license_id": self.lic.id, "license": self.license_name}
        if next_url:
            state_payload["next"] = next_url
        qs = {
            "app_token": self.app_token,
            "redirect_uri": redirect_uri,
            "state": make_state(state_payload),
        }
        return f"{login_base}?{urlencode(qs)}"

    def exchange_code_for_access_token(self, code: str) -> str:
        token_url = f"{self.api_base}/oauth/access_token/"
        basic = base64.b64encode(f"{self.app_token}:{self.app_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"code": code, "grant_type": "authorization_code"}
        resp = requests.post(token_url, headers=headers, data=data, timeout=20)
        if resp.status_code == 405 or (resp.status_code >= 400 and "GET" in (resp.text or "").upper()):
            resp = requests.get(token_url, headers=headers, params=data, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise ValueError(f"Resposta sem access_token: {payload}")
        return access_token

    def save_access_token(self, access_token: str) -> LicenseIntegration:
        """Salva o token (criptografado via EncryptedTextField) para ESTA licença."""
        obj, _ = LicenseIntegration.objects.get_or_create(license=self.lic)
        obj.access_token = access_token
        obj.connected_at = obj.connected_at or timezone.now()
        obj.is_active = True
        obj.save(update_fields=["access_token", "connected_at", "is_active"])
        return obj

    @staticmethod
    def auth_headers(access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    def verificar_conexao(self) -> tuple[bool, dict | None]:
        obj = LicenseIntegration.objects.filter(license=self.lic, is_active=True).first()
        if not obj or not obj.access_token:
            return False, {"error": "Licença não conectada ou sem token salvo."}
        url = f"{self.api_base}{settings.SUPERLOGICA_HEALTHCHECK_PATH}"
        try:
            resp = requests.get(url, headers=self.auth_headers(obj.access_token), timeout=20)
            ok = 200 <= resp.status_code < 300
            payload = (
                resp.json()
                if (resp.headers.get("Content-Type", "") or "").startswith("application/json")
                else {"status_code": resp.status_code}
            )
            obj.last_verified_at = timezone.now()
            obj.save(update_fields=["last_verified_at"])
            return ok, payload
        except Exception as e:
            logger.exception("Falha ao verificar conexão com %s", self.license_name)
            return False, {"error": str(e)}

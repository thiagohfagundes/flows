# clientes/middleware.py
from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse
from django.utils.deprecation import MiddlewareMixin

STEP_ROUTE_NAMES = {
    "perfil":     "clientes:onboarding_perfil",
    "empresa":    "clientes:onboarding_empresa",
    "integracao": "clientes:onboarding_integracao",
    "processo":   "clientes:onboarding_processo",
    "resumo":     "clientes:onboarding_resumo",
}

ALLOWLIST_PATH_PREFIXES = (
    "/admin/", "/static/", "/media/", "/favicon.ico",
    "/api/public/", "/healthz", "/readyz",
)

ALLOWLIST_NAMES = {
    "clientes:login", "clientes:logout", "clientes:registro",
    "kanban:pipeline_create", "kanban_templates:template_list",
}

# já libera todas as rotas do onboarding
ALLOWLIST_CONTAINS = "/onboarding/"

class OnboardingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)

        # não logado / staff / superuser -> ignora
        if not user or not user.is_authenticated:
            return None
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return None

        # se a sessão já marcou como concluído, libera
        if request.session.get("onboarding_completed"):
            return None

        path = request.path_info or "/"

        # rotas públicas e arquivos estáticos
        if any(path.startswith(p) for p in ALLOWLIST_PATH_PREFIXES):
            return None

        # todas as urls de onboarding ficam liberadas
        if ALLOWLIST_CONTAINS in path:
            return None

        # allowlist por nome de rota (login/logout/registro e os destinos do kanban)
        try:
            match = resolve(path)
            full_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
            if full_name in ALLOWLIST_NAMES:
                return None
        except Resolver404:
            # se não conseguiu resolver, não arrisca bloquear
            return None

        # pega/garante o estado de onboarding
        onboarding = getattr(user, "onboarding", None) or self._ensure_onboarding_state(user)

        # se não tem estado, ou se já concluiu, libera
        if not onboarding:
            return None

        # ✅ se concluiu no banco, cacheia na sessão e libera
        if self._is_completed(onboarding):
            request.session["onboarding_completed"] = True
            return None

        # ainda não concluiu -> redireciona para o passo atual
        step = getattr(onboarding, "current_step", "perfil") or "perfil"
        route_name = STEP_ROUTE_NAMES.get(step, STEP_ROUTE_NAMES["perfil"])
        return redirect(reverse(route_name))

    def _is_completed(self, onboarding):
        if hasattr(onboarding, "is_completed") and callable(onboarding.is_completed):
            return onboarding.is_completed()
        return bool(getattr(onboarding, "onboarding_completed_at", None))

    def _ensure_onboarding_state(self, user):
        try:
            from clientes.models_onboarding import OnboardingState
        except Exception:
            try:
                from usuarios.models import OnboardingState
            except Exception:
                return None
        obj, _ = OnboardingState.objects.get_or_create(user=user)
        return obj

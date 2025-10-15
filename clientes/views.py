from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from clientes.models import OnboardingState
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

from .forms import UserForm, PessoaForm, EmpresaQuickForm, ClienteLicenseForm
from .models import Empresa, ClienteLicense, Pessoa

# Create your views here.
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/pipelines")  
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("clientes:login")


def register_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]

        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Conta criada com sucesso! 🎉")
            return redirect("/pipelines")

    return render(request, "auth/register.html")

@login_required
def perfil(request):
    pessoa = request.user.pessoa  # graças ao OneToOneField
    user_form = UserForm(instance=request.user)
    pessoa_form = PessoaForm(instance=pessoa)
    empresa_form = EmpresaQuickForm()
    licencas = ClienteLicense.objects.filter(
        cliente__usuario=request.user  # ajuste para sua modelagem de dono da licença
    ).select_related('integracao', 'cliente')

    if request.method == "POST" and request.POST.get("which") == "nova_licenca":
        form = ClienteLicenseForm(request.POST, user=request.user)
        if form.is_valid():
            lic = form.save()
            messages.success(request, f"Licença {lic.license_name} criada.")
            return redirect(request.path)  # recarrega a página
        else:
            licenca_form = form  # mantém erros no template
    else:
        licenca_form = ClienteLicenseForm(user=request.user)

    if request.method == "POST":
        which = request.POST.get("which", "perfil")
        if which == "perfil":
            user_form = UserForm(request.POST, instance=request.user)
            pessoa_form = PessoaForm(request.POST, request.FILES, instance=pessoa)
            if user_form.is_valid() and pessoa_form.is_valid():
                user_form.save()
                pessoa_form.save()
                messages.success(request, "Perfil atualizado com sucesso!")
                return redirect("clientes:perfil_usuario")
        elif which == "empresa":
            empresa_form = EmpresaQuickForm(request.POST)
            if empresa_form.is_valid():
                emp = empresa_form.save(commit=False)
                emp.criado_por = request.user
                emp.responsavel = pessoa
                emp.save()
                emp.colaboradores.add(pessoa)
                messages.success(request, "Empresa criada e vinculada!")
                return redirect("clientes:perfil_usuario")

    minhas_empresas = Empresa.objects.filter(colaboradores=pessoa).order_by("-data_ult_modificacao")[:8]
    return render(request, "clientes/perfil.html", {
        "user_form": user_form,
        "pessoa_form": pessoa_form,
        "empresa_form": empresa_form,
        "pessoa": pessoa,
        "licencas": licencas,
        "minhas_empresas": minhas_empresas,
        "licenca_form": licenca_form,
    })

# TELA DA EMPRESA

def user_can_access_empresa(user, empresa):
    # Ajuste conforme sua regra; por enquanto: quem criou ou é colaborador
    if empresa.criado_por_id == user.id:
        return True
    if empresa.colaboradores.filter(pk=getattr(user, "pessoa", None) and user.pessoa.pk).exists():
        return True
    # se a relação for diferente, adapte
    return False

@login_required
def empresa_settings(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not (empresa.criado_por_id == request.user.id or empresa.colaboradores.filter(pk=getattr(request.user, "pessoa", None) and request.user.pessoa.pk).exists()):
        return HttpResponseForbidden("Você não tem permissão para ver esta página.")
    # Rendeiza a página principal; conteúdo das abas carregado por HTMX
    return render(request, "clientes/empresa.html", {"empresa": empresa})


@login_required
def empresa_info_partial(request, pk):
    """
    GET -> retorna partial com info (ou form se editar)
    POST -> valida e salva, e retorna partial atualizado (HTMX)
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    # permissões (mesma regra)
    if not (empresa.criado_por_id == request.user.id or empresa.colaboradores.filter(pk=getattr(request.user, "pessoa", None) and request.user.pessoa.pk).exists()):
        return HttpResponseForbidden("Sem permissão.")

    # se POST: salvar form (htmx)
    if request.method == "POST":
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            # após salvar, retornar o fragmento de visualização atualizado
            html = render_to_string("clientes/partials/_empresa_info.html", {"empresa": empresa, "form": None, "request": request})
            return HttpResponse(html)
        else:
            # retornar o form com erros
            html = render_to_string("clientes/partials/_empresa_info_form.html", {"empresa": empresa, "form": form, "request": request})
            return HttpResponse(html)

    # GET: se query param edit for true ou chamada a /edit/ então retorna form
    edit = request.GET.get("edit") == "1" or request.path.endswith("/edit/")
    if edit:
        form = EmpresaForm(instance=empresa)
        return render(request, "clientes/partials/_empresa_info_form.html", {"empresa": empresa, "form": form})
    else:
        return render(request, "clientes/partials/_empresa_info.html", {"empresa": empresa})


@login_required
def empresa_colaboradores_partial(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not (empresa.criado_por_id == request.user.id or empresa.colaboradores.filter(pk=getattr(request.user, "pessoa", None) and request.user.pessoa.pk).exists()):
        return HttpResponseForbidden("Sem permissão.")
    return render(request, "clientes/partials/_empresa_colaboradores.html", {"empresa": empresa})


@login_required
def empresa_licencas_partial(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not (empresa.criado_por_id == request.user.id or empresa.colaboradores.filter(pk=getattr(request.user, "pessoa", None) and request.user.pessoa.pk).exists()):
        return HttpResponseForbidden("Sem permissão.")
    # stub por enquanto
    return render(request, "clientes/partials/_empresa_licencas.html", {"empresa": empresa})

@login_required
def empresa_colaboradores_partial(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not user_can_access_empresa(request.user, empresa):
        return HttpResponseForbidden("Sem permissão.")
    return render(request, "clientes/partials/_empresa_colaboradores.html", {"empresa": empresa})

@login_required
def empresa_remove_colaborador_confirm(request, pk, pessoa_pk):
    """
    Retorna o conteúdo do modal de confirmação (HTMX GET).
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    if not user_can_access_empresa(request.user, empresa):
        return HttpResponseForbidden("Sem permissão.")
    pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
    # não permitir tentar remover responsavel ou causar inconsistência aqui também opcionalmente
    # apenas devolvemos o modal; a verificação final acontece no POST
    return render(request, "clientes/partials/_confirm_remove_colaborador_modal.html", {"empresa": empresa, "pessoa": pessoa})


@login_required
@require_POST
def empresa_remove_colaborador(request, pk, pessoa_pk):
    """
    POST via HTMX: espera campo 'confirm_name' com o nome exato da pessoa.
    Se válido, remove a relação many-to-many e retorna partial atualizado.
    Caso contrário, retorna o modal com erro (status 400).
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    if not user_can_access_empresa(request.user, empresa):
        return HttpResponseForbidden("Sem permissão.")
    pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)

    # Proteção: usuário não pode remover a si mesmo
    if getattr(pessoa, "usuario", None) == request.user:
        # retorna o modal com mensagem de erro
        context = {"empresa": empresa, "pessoa": pessoa, "error": "Você não pode remover a si próprio."}
        html = render_to_string("clientes/partials/_confirm_remove_colaborador_modal.html", context, request=request)
        return HttpResponse(html, status=400)

    confirm_name = request.POST.get("confirm_name", "").strip()

    # Verifica igualdade exata (case-sensitive). Se preferir case-insensitive, use .lower()
    if confirm_name != (pessoa.nome or ""):
        context = {"empresa": empresa, "pessoa": pessoa, "error": "Nome digitado não confere. Digite o nome completo para confirmar."}
        html = render_to_string("clientes/partials/_confirm_remove_colaborador_modal.html", context, request=request)
        return HttpResponse(html, status=400)

    # tudo ok: remove a relação many-to-many (não deleta Pessoa)
    empresa.colaboradores.remove(pessoa)
    empresa.save()

    # após remoção, retornamos a lista atualizada de colaboradores (partial)
    return render(request, "clientes/partials/_empresa_colaboradores.html", {"empresa": empresa})

@login_required
def empresa_edit_colaborador(request, pk, pessoa_pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not user_can_access_empresa(request.user, empresa):
        return HttpResponseForbidden("Sem permissão.")
    pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
    # GET -> devolve form parcial; POST -> salva e retorna partial atualizado
    if request.method == "POST":
        form = PessoaForm(request.POST, instance=pessoa)
        if form.is_valid():
            form.save()
            return render(request, "clientes/partials/_empresa_colaboradores.html", {"empresa": empresa})
        else:
            return render(request, "clientes/partials/_colaborador_edit_form.html", {"form": form, "empresa": empresa, "pessoa": pessoa})
    else:
        form = PessoaForm(instance=pessoa)
        return render(request, "clientes/partials/_colaborador_edit_form.html", {"form": form, "empresa": empresa, "pessoa": pessoa})

@login_required
def empresa_colaborador_permissoes(request, pk, pessoa_pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if not user_can_access_empresa(request.user, empresa):
        return HttpResponseForbidden("Sem permissão.")
    pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
    # stub — aqui você cria o formulário/lista de permissões reais
    return render(request, "clientes/colaborador_permissoes.html", {"empresa": empresa, "pessoa": pessoa})

# ------------------------------- ONBOARDING -----------------------------------
from django.utils.decorators import method_decorator
from django.views import View
from .forms import PessoaForm, EmpresaForm, IntegracaoForm, PrimeiroProcessoForm
from .models import Empresa, ClienteLicense, OnboardingState, OnboardingStep
from .services import get_or_create_pessoa_for_user

def _next(step):
    order = [
        OnboardingStep.PERFIL,
        OnboardingStep.EMPRESA,
        OnboardingStep.INTEGRACAO,
        OnboardingStep.PROCESSO,
        OnboardingStep.RESUMO,
    ]
    idx = order.index(step)
    return order[idx + 1] if idx + 1 < len(order) else None

@method_decorator(login_required, name="dispatch")
class PerfilView(View):
    template_name = "onboarding/perfil.html"

    def get(self, request):
        pessoa = get_or_create_pessoa_for_user(request.user)
        form = PessoaForm(instance=pessoa)
        return render(request, self.template_name, {"form": form, "step": "perfil"})

    def post(self, request):
        pessoa = get_or_create_pessoa_for_user(request.user)
        form = PessoaForm(request.POST, instance=pessoa)
        if form.is_valid():
            form.save()
            ob = request.user.onboarding
            ob.advance(_next(OnboardingStep.PERFIL))
            return redirect("clientes:onboarding_empresa")
        return render(request, self.template_name, {"form": form, "step": "perfil"})

@method_decorator(login_required, name="dispatch")
class EmpresaView(View):
    template_name = "onboarding/empresa.html"

    def get(self, request):
        form = EmpresaForm()
        return render(request, self.template_name, {"form": form, "step": "empresa"})

    def post(self, request):
        form = EmpresaForm(request.POST)
        if form.is_valid():
            empresa: Empresa = form.save(commit=False)
            empresa.criado_por = request.user
            pessoa = get_or_create_pessoa_for_user(request.user)
            empresa.responsavel = pessoa
            empresa.save()
            empresa.colaboradores.add(pessoa)

            ob = request.user.onboarding
            ob.advance(_next(OnboardingStep.EMPRESA))
            return redirect("clientes:onboarding_integracao")
        return render(request, self.template_name, {"form": form, "step": "empresa"})

@method_decorator(login_required, name="dispatch")
class IntegracaoView(View):
    template_name = "onboarding/integracao.html"

    def get(self, request):
        form = IntegracaoForm()
        return render(request, self.template_name, {"form": form, "step": "integracao"})

    def post(self, request):
        # Dois caminhos: salvar licença OU pular integração
        if "pular" in request.POST:
            ob = request.user.onboarding
            ob.advance(_next(OnboardingStep.INTEGRACAO))
            return redirect("clientes:onboarding_processo")

        pessoa = get_or_create_pessoa_for_user(request.user)
        form = IntegracaoForm(request.POST)
        if form.is_valid():
            lic: ClienteLicense = form.save(commit=False)
            lic.cliente = pessoa
            lic.save()
            # aqui no futuro: validar subdomínio/handshake com a API do Superlógica
            ob = request.user.onboarding
            ob.advance(_next(OnboardingStep.INTEGRACAO))
            return redirect("clientes:onboarding_processo")
        return render(request, self.template_name, {"form": form, "step": "integracao"})

@method_decorator(login_required, name="dispatch")
class PrimeiroProcessoView(View):
    template_name = "onboarding/processo.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PrimeiroProcessoForm(), "step": "processo"})

    def post(self, request):
        form = PrimeiroProcessoForm(request.POST)
        if form.is_valid():
            # TODO: substituir por seu modelo real de "processo"
            # Exemplo mínimo: salvar num model genérico ou chamar um service
            # create_primeiro_processo(user=request.user, **form.cleaned_data)
            ob = request.user.onboarding
            ob.advance(_next(OnboardingStep.PROCESSO))
            return redirect("clientes:onboarding_resumo")
        return render(request, self.template_name, {"form": form, "step": "processo"})

@method_decorator(login_required, name="dispatch")
class ResumoView(View):
    template_name = "onboarding/resumo.html"

    def get(self, request):
        pessoa = get_or_create_pessoa_for_user(request.user)
        licencas = pessoa.licencas.all()
        empresas = pessoa.empresa.all()
        return render(request, self.template_name, {
            "pessoa": pessoa,
            "licencas": licencas,
            "empresas": empresas,
            "step": "resumo"
        })

    def post(self, request):
        # concluir
        ob: OnboardingState = request.user.onboarding
        ob.complete()
        return redirect(reverse("dashboard"))  # ajuste para a rota inicial do app

class ProcessChoiceView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        choice = request.POST.get("choice")
        if choice not in {"blank", "template"}:
            return HttpResponseBadRequest("Escolha inválida.")

        target = reverse("kanban:pipeline_create") if choice == "blank" else reverse("kanban_templates:template_list")

        # ✅ marca como concluído (DB) + sessão
        self._complete_onboarding(request.user)
        request.session["onboarding_completed"] = True
        request.session.modified = True

        return redirect(target)

    def _complete_onboarding(self, user):
        """
        Ajuste para o seu modelo. Exemplo 1: OnboardingState.
        Exemplo 2: campo na Pessoa.
        """
        # Exemplo 1: modelo dedicado
        try:
            ob, _ = OnboardingState.objects.get_or_create(user=user)
            ob.current_step = "resumo"
            ob.onboarding_completed_at = timezone.now()
            ob.save(update_fields=["current_step", "onboarding_completed_at"])
            return
        except Exception:
            pass

        # Exemplo 2: campo na Pessoa (boolean ou datetime)
        try:
            pessoa = user.pessoa
            if hasattr(pessoa, "onboarding_completed_at"):
                pessoa.onboarding_completed_at = timezone.now()
                pessoa.save(update_fields=["onboarding_completed_at"])
                return
            if hasattr(pessoa, "onboarding_completed"):
                pessoa.onboarding_completed = True
                pessoa.save(update_fields=["onboarding_completed"])
                return
        except Exception:
            pass


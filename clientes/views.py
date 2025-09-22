from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import UserForm, PessoaForm, EmpresaQuickForm, ClienteLicenseForm
from .models import Empresa, ClienteLicense

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
                return redirect("perfil")
        elif which == "empresa":
            empresa_form = EmpresaQuickForm(request.POST)
            if empresa_form.is_valid():
                emp = empresa_form.save(commit=False)
                emp.criado_por = request.user
                emp.responsavel = pessoa
                emp.save()
                emp.colaboradores.add(pessoa)
                messages.success(request, "Empresa criada e vinculada!")
                return redirect("perfil")

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
            from usuarios.models import OnboardingState
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
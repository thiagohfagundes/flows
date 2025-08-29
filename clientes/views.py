from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

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
            return redirect("/kanban/pipelines/")  
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


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
            return redirect("/kanban/pipelines/")

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
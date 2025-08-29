# clientes/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Pessoa, Empresa, ClienteLicense
import re

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = [
            "nome", "cargo", "telefone", "cidade",
            "biografia", "linkedin_url", "website_url",
            "data_nascimento", "recebe_emails"
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "biografia": forms.Textarea(attrs={"rows": 4}),
        }

class EmpresaQuickForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ["nome", "tipo", "cidade", "telefone", "email"]

BASE_INPUT = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg w-full p-2.5"

class ClienteLicenseForm(forms.ModelForm):
    class Meta:
        model = ClienteLicense
        fields = ["cliente", "license_name", "apelido"]
        widgets = {
            "cliente": forms.Select(attrs={"class": BASE_INPUT}),
            "license_name": forms.TextInput(
                attrs={"placeholder": "apenas o subdomínio (ex: minhaimobiliaria)", "class": BASE_INPUT}
            ),
            "apelido": forms.TextInput(
                attrs={"placeholder": "opcional (ex: Matriz Curitiba)", "class": BASE_INPUT}
            ),
        }
        help_texts = {
            "license_name": "Sem https:// e sem .superlogica.net — só o subdomínio.",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["cliente"].queryset = Pessoa.objects.filter(usuario=user)

    def clean_license_name(self):
        name = (self.cleaned_data["license_name"] or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9-]+", name):
            raise forms.ValidationError("Use apenas letras minúsculas, números e hífen.")
        return name

    def clean_apelido(self):
        ap = (self.cleaned_data.get("apelido") or "").strip()
        return ap or None

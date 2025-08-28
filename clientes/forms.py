# clientes/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Pessoa, Empresa

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

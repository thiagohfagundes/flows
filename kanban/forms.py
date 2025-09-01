from django import forms
from .models import Checklist, Pipeline  # ajuste o import se o modelo tiver outro nome

class PipelineForm(forms.ModelForm):
    class Meta:
        model = Pipeline
        fields = ["nome", "descricao"]  # adicione outros campos se quiser
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg w-full p-2.5"
            }),
            "descricao": forms.Textarea(attrs={
                "rows": 4,
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg w-full p-2.5"
            }),
        }


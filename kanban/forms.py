from django import forms
from .models import Pipeline

BASE_INPUT_CLS = "w-full rounded-lg border px-3 py-2"
BASE_SELECT_CLS = "w-full rounded-lg border px-3 py-2"
BASE_NUMBER_CLS = "w-32 rounded-lg border px-3 py-2"
BASE_TEXTAREA_CLS = "w-full rounded-lg border px-3 py-2"

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

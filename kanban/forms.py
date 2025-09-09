from django import forms
from .models import Pipeline, Checklist, ChecklistItem, Etapa
from django.forms import inlineformset_factory

BASE_INPUT_CLS = "w-full rounded-lg border px-3 py-2"
BASE_SELECT_CLS = "w-full rounded-lg border px-3 py-2"
BASE_NUMBER_CLS = "w-32 rounded-lg border px-3 py-2"
BASE_TEXTAREA_CLS = "w-full rounded-lg border px-3 py-2"

class ChecklistForm(forms.ModelForm):
    class Meta:
        model = Checklist
        fields = ["nome", "descricao"]  # ordem e pipeline vêm da view
        widgets = {
            "nome": forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
            "descricao": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
        }

class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = [
            "titulo", "descricao", "obrigatorio",
            "prazo_dias", "atribuido_a", "requer_aprovacao",
            "vinculado_a_etapa",   # <- novo nome
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
            "descricao": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
            "obrigatorio": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "prazo_dias": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
            "atribuido_a": forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
            "requer_aprovacao": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "vinculado_a_etapa": forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm"}),
        }

    def __init__(self, *args, **kwargs):
        pipeline = kwargs.pop("pipeline", None)  # passado pela view
        super().__init__(*args, **kwargs)
        if pipeline is not None:
            self.fields["vinculado_a_etapa"].queryset = Etapa.objects.filter(pipelines=pipeline)

ChecklistItemFormSet = inlineformset_factory(
    Checklist,
    ChecklistItem,
    form=ChecklistItemForm,
    fields=["titulo","descricao","obrigatorio","prazo_dias","atribuido_a","requer_aprovacao","vinculado_a_etapa"],
    extra=0,
    can_delete=True,
)


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

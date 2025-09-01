from datetime import timedelta
from django.utils import timezone
from .models import Checklist, ChecklistItem, Tarefa

def tarefas_para_card(card):
    """
    Gera tarefas de acordo com checklists do pipeline e da etapa atual do card.
    Não duplica tarefas já geradas a partir do mesmo ChecklistItem.
    """
    pass
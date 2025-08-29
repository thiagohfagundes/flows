# signals.py (registre em apps.py ready())
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Card, Propriedade, PipelinePropriedade

@receiver(post_save, sender=Card)
def card_create_default_properties(sender, instance: Card, created, **kwargs):
    if not created:
        return
    defs = PipelinePropriedade.objects.filter(pipeline=instance.pipeline).order_by('ordem', 'id')
    to_create = [
        Propriedade(card=instance, definicao=d, valor=d.valor_padrao)
        for d in defs
    ]
    Propriedade.objects.bulk_create(to_create)

# clientes/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Pessoa

@receiver(post_save, sender=User)
def create_or_update_pessoa(sender, instance, created, **kwargs):
    if created:
        Pessoa.objects.create(usuario=instance, nome=instance.get_full_name() or instance.username, email=instance.email)
    else:
        # mantém e-mail sincronizado se desejar
        if hasattr(instance, "pessoa") and instance.email and not instance.pessoa.email:
            instance.pessoa.email = instance.email
            instance.pessoa.save()
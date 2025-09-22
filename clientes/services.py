from .models import Pessoa

def get_or_create_pessoa_for_user(user):
    pessoa, _ = Pessoa.objects.get_or_create(usuario=user, defaults={
        "nome": user.get_full_name() or user.get_username(),
        "email": user.email or "",
    })
    return pessoa
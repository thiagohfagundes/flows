# kanban/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .forms import PipelineForm
from .models import Pipeline, Etapa, Card, Tarefa, STATUS_TAREFA, STATUS_ETAPA

def home(request):
    return render(request, "kanban/home.html")

# -------------------------
# PIPES: listar e detalhar
# -------------------------

@login_required
def pipeline_list(request):
    pipelines = Pipeline.objects.filter(criado_por=request.user).order_by("-data_criacao")
    return render(request, "kanban/pipeline_list.html", {"pipelines": pipelines})

# sugestões iniciais (ajuste os nomes se quiser)
DEFAULT_STAGE_SUGGESTIONS = [
    {"nome": "Contato inicial", "status": "ABERTO"},
    {"nome": "Qualificação",    "status": "ABERTO"},
    {"nome": "Em execução",     "status": "ABERTO"},
    {"nome": "Concluído",       "status": "CONCLUIDO"},
]

@login_required
@require_http_methods(["GET", "POST"])
def pipeline_create(request):
    """
    Cria pipeline. A ordem das etapas vem da ordem dos campos no form (SortableJS).
    Não exibimos 'posicao' — calculamos como 10, 20, 30…
    """
    context = {
        "statuses": STATUS_ETAPA,
        "defaults": DEFAULT_STAGE_SUGGESTIONS,
    }

    if request.method == "POST":
        nome = (request.POST.get("nome") or "").strip()
        if not nome:
            context.update({"erro": "Nome é obrigatório.", "nome": nome})
            # mantém valores já digitados para não perder o que o usuário fez
            context["posted_rows"] = list(zip(
                request.POST.getlist("etapas-nome"),
                request.POST.getlist("etapas-status"),
            ))
            return render(request, "kanban/pipeline_create.html", context)

        with transaction.atomic():
            pipeline = Pipeline.objects.create(
                nome=nome,
                descricao=(request.POST.get("descricao") or "").strip() or None,
                criado_por=request.user,
            )

            # Etapas em ordem: o browser envia na ordem atual do DOM
            nomes  = request.POST.getlist("etapas-nome")
            stats  = request.POST.getlist("etapas-status")

            pos = 10
            for i, n in enumerate(nomes):
                n = (n or "").strip()
                if not n:
                    continue
                status_i = stats[i] if i < len(stats) and stats[i] else "ABERTO"

                etapa = Etapa.objects.create(
                    nome=n,
                    posicao=pos,
                    status=status_i,
                    criado_por=request.user,
                )
                pipeline.etapas.add(etapa)
                pos += 10

        return redirect("kanban:pipeline_detail", pipeline_id=pipeline.id)

    # GET
    return render(request, "kanban/criar_pipeline.html", context)

@login_required
@require_http_methods(["POST"])
def pipeline_delete(request, pk):
    pipeline = get_object_or_404(Pipeline, pk=pk, criado_por=request.user)  # filtre por dono se quiser
    pipeline.delete()
    # Como hx-swap="outerHTML" e target é a <tr>, devolver vazio remove a linha
    return HttpResponse("")  # 200 OK com corpo vazio

@login_required
def pipeline_detail(request, pipeline_id):
    pipeline = get_object_or_404(Pipeline, id=pipeline_id, criado_por=request.user)
    etapas = pipeline.etapas.order_by("posicao").prefetch_related("tarefas", "tickets")
    # tickets = related_name em Card(etapa=...) é "tickets", então usamos isso.
    return render(request, "kanban/pipeline_detail.html", {"pipeline": pipeline, "etapas": etapas})

@login_required
def pipeline_edit(request, pk):
    # se você tiver o campo criado_por, mantenha o filtro para garantir propriedade
    filtro = {"pk": pk}
    if hasattr(Pipeline, "criado_por"):
        filtro["criado_por"] = request.user

    pipeline = get_object_or_404(Pipeline, **filtro)

    if request.method == "POST":
        form = PipelineForm(request.POST, instance=pipeline)
        if form.is_valid():
            form.save()
            messages.success(request, "Pipeline atualizado com sucesso.")
            return redirect("kanban:pipeline_detail", pk=pipeline.pk)
    else:
        form = PipelineForm(instance=pipeline)

    return render(request, "kanban/pipeline_form.html", {
        "form": form,
        "pipeline": pipeline,
        "is_edit": True,
    })

# -------------------------
# ETAPAS
# -------------------------

@login_required
@require_http_methods(["POST"])
def etapa_create(request, pipeline_id):
    pipeline = get_object_or_404(Pipeline, id=pipeline_id, criado_por=request.user)
    nome = request.POST.get("nome", "").strip()
    descricao = request.POST.get("descricao", "").strip()
    if not nome:
        return HttpResponseBadRequest("Nome é obrigatório")

    # calcula próxima posição simples (maior posicao + 10)
    last = pipeline.etapas.order_by("-posicao").first()
    proxima_pos = (last.posicao + 10) if last else 10

    etapa = Etapa.objects.create(
        nome=nome,
        descricao=descricao or None,
        posicao=proxima_pos,
        criado_por=request.user,
    )
    pipeline.etapas.add(etapa)

    # retorna HTML parcial da coluna nova para swap
    return render(request, "kanban/partials/coluna.html", {"etapa": etapa, "pipeline": pipeline})

@login_required
@require_http_methods(["POST"])
def etapa_edit(request, etapa_id):
    etapa = get_object_or_404(Etapa, id=etapa_id, criado_por=request.user)
    nome = request.POST.get("nome", "").strip()
    descricao = request.POST.get("descricao", "").strip()
    posicao = request.POST.get("posicao")
    if nome:
        etapa.nome = nome
    etapa.descricao = descricao or None
    if posicao:
        try:
            etapa.posicao = int(posicao)
        except ValueError:
            pass
    etapa.save(update_fields=["nome", "descricao", "posicao"])

    # devolve o header atualizado da coluna para swap inline
    return render(request, "kanban/partials/coluna_header.html", {"etapa": etapa})


@login_required
def pipeline_create_stage_row(request):
    return render(request, "kanban/partials/pipeline_stage_row.html", {"statuses": STATUS_ETAPA})

# -------------------------
# CARDS
# -------------------------

@login_required
def card_detail(request, card_id):
    card = get_object_or_404(
        Card.objects.select_related("etapa", "pipeline", "criado_por")
            .prefetch_related("tarefas"),
        id=card_id
    )
    # counts para progresso
    total = card.tarefas.count()
    done = card.tarefas.filter(concluido=True).count()
    ctx = {"card": card, "total": total, "done": done}
    return render(request, "kanban/partials/card_drawer.html", ctx)

@login_required
@require_http_methods(["POST"])
def card_create(request, pipeline_id):
    pipeline = get_object_or_404(Pipeline, id=pipeline_id, criado_por=request.user)
    titulo = request.POST.get("titulo", "").strip()
    descricao = request.POST.get("descricao", "").strip()
    etapa_id = request.POST.get("etapa_id")

    if not titulo or not etapa_id:
        return HttpResponseBadRequest("Título e etapa são obrigatórios")

    etapa = get_object_or_404(Etapa, id=etapa_id)
    # garante que a etapa pertence ao pipeline
    if not pipeline.etapas.filter(id=etapa.id).exists():
        return HttpResponseBadRequest("Etapa não pertence a este pipeline")

    card = Card.objects.create(
        titulo=titulo,
        descricao=descricao or None,
        etapa=etapa,
        pipeline=pipeline,
        criado_por=request.user,
        atribuido_a=request.user,  # opcional
    )

    # retorna o card renderizado para injetar na coluna com htmx
    return render(request, "kanban/partials/card.html", {"card": card})

@login_required
@require_http_methods(["POST"])
def card_edit(request, card_id):
    card = get_object_or_404(Card, id=card_id, criado_por=request.user)
    card.titulo = request.POST.get("titulo", card.titulo).strip() or card.titulo
    card.descricao = (request.POST.get("descricao") or "").strip() or None
    etapa_id = request.POST.get("etapa_id")
    if etapa_id:
        etapa = get_object_or_404(Etapa, id=etapa_id)
        # se o card tem pipeline, respeita a associação da etapa ao pipeline
        if card.pipeline and not card.pipeline.etapas.filter(id=etapa.id).exists():
            return HttpResponseBadRequest("Etapa inválida para este pipeline")
        card.etapa = etapa
    card.data_ult_modificacao = timezone.now()
    card.save()
    return render(request, "kanban/partials/card.html", {"card": card})

@login_required
@require_http_methods(["POST"])
def card_delete(request, card_id):
    card = get_object_or_404(Card, id=card_id, criado_por=request.user)
    etapa_id = card.etapa_id
    card.delete()
    # devolve um 204 para htmx remover o elemento
    return HttpResponse(status=204)

@login_required
@require_http_methods(["POST"])
def card_move(request, card_id):
    """
    Move o card para outra etapa (via DnD). Como não há campo de ordenação no Card,
    somente atualizamos a etapa. A ordenação na coluna segue data_criacao.
    """
    card = get_object_or_404(Card, id=card_id)
    new_etapa_id = request.POST.get("etapa_id")
    if not new_etapa_id:
        return HttpResponseBadRequest("etapa_id é obrigatório")
    new_etapa = get_object_or_404(Etapa, id=new_etapa_id)

    # valida pipeline consistente (se o card tiver pipeline definido)
    if card.pipeline and not card.pipeline.etapas.filter(id=new_etapa.id).exists():
        return HttpResponseBadRequest("Etapa não pertence ao mesmo pipeline")

    with transaction.atomic():
        card.etapa = new_etapa
        card.data_ult_modificacao = timezone.now()
        card.save(update_fields=["etapa", "data_ult_modificacao"])

    # devolve o card renderizado (p/ reconciliação ou ignorar com swap=none)
    return render(request, "kanban/partials/card.html", {"card": card})

# -------------------------
# TAREFAS (opcionais)
# -------------------------

@login_required
@require_http_methods(["POST"])
def tarefa_create(request, card_id):
    card = get_object_or_404(Card, id=card_id)
    titulo = request.POST.get("titulo", "").strip()
    if not titulo:
        return HttpResponseBadRequest("Título é obrigatório")
    tarefa = Tarefa.objects.create(
        titulo=titulo,
        card=card,
        criado_por=request.user,
        etapa=card.etapa,
        status="ABERTO",
    )
    return render(request, "kanban/partials/tarefa.html", {"tarefa": tarefa})

@login_required
@require_http_methods(["POST"])
def tarefa_toggle(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    tarefa.concluido = not tarefa.concluido
    tarefa.status = "CONCLUIDO" if tarefa.concluido else "ABERTO"
    tarefa.data_conclusao = timezone.now() if tarefa.concluido else None
    tarefa.save(update_fields=["concluido", "status", "data_conclusao"])
    return render(request, "kanban/partials/tarefa.html", {"tarefa": tarefa})

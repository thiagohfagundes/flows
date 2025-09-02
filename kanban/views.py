# kanban/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseBadRequest, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db.models import Prefetch
from .models import Pipeline, Etapa, Card, Tarefa, PipelinePropriedade, Propriedade, Checklist, STATUS_TAREFA, STATUS_ETAPA, TIPOS_PROPRIEDADE

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
    Agora também cria as definições de propriedades do pipeline.
    """
    context = {
        "statuses": STATUS_ETAPA,
        "defaults": DEFAULT_STAGE_SUGGESTIONS,
        "TIPOS_PROPRIEDADE": TIPOS_PROPRIEDADE,
    }

    if request.method == "POST":
        nome = (request.POST.get("nome") or "").strip()

        # sempre preservar o que o usuário já digitou
        context["nome"] = nome
        context["descricao"] = (request.POST.get("descricao") or "").strip() or ""

        # etapas já postadas (para repintar a tabela em caso de erro)
        context["posted_rows"] = list(zip(
            request.POST.getlist("etapas-nome"),
            request.POST.getlist("etapas-status"),
        ))

        # propriedades já postadas (para repintar em caso de erro)
        def _posted_props():
            # monta uma lista de dicts com os campos do form de propriedade
            nomes  = request.POST.getlist("prop_nome")
            tipos  = request.POST.getlist("prop_tipo")
            obrigs = request.POST.getlist("prop_obrigatorio")
            opcs   = request.POST.getlist("prop_opcoes")
            defs   = request.POST.getlist("prop_valor_padrao")
            ordem  = request.POST.getlist("prop_ordem")
            out = []
            for i in range(max(len(nomes), len(tipos), len(obrigs), len(opcs), len(defs), len(ordem))):
                out.append({
                    "nome": (nomes[i] if i < len(nomes) else "") or "",
                    "tipo": (tipos[i] if i < len(tipos) else "") or "",
                    "obrigatorio": (obrigs[i] if i < len(obrigs) else "") == "on",
                    "opcoes": (opcs[i] if i < len(opcs) else "") or "",
                    "valor_padrao": (defs[i] if i < len(defs) else "") or "",
                    "ordem": (ordem[i] if i < len(ordem) else "") or "",
                })
            return out

        if not nome:
            context.update({"erro": "Nome é obrigatório.", "posted_props": _posted_props()})
            return render(request, "kanban/criar_pipeline.html", context)

        # validação básica das propriedades antes de criar qualquer coisa
        props_postadas = _posted_props()
        # regra: se tipo == select e sem opções, erro
        for p in props_postadas:
            if p["nome"].strip() == "":
                # deixar passar linhas vazias (usuário pode ter clicado e não preenchido)
                continue
            if p["tipo"] == "select":
                has_opts = bool([o.strip() for o in (p["opcoes"] or "").split(";") if o.strip()])
                if not has_opts:
                    context.update({
                        "erro": f"A propriedade '{p['nome'] or '(sem nome)'}' é do tipo seleção e precisa de opções (ex.: A;B;C).",
                        "posted_props": props_postadas,
                    })
                    return render(request, "kanban/criar_pipeline.html", context)

        with transaction.atomic():
            pipeline = Pipeline.objects.create(
                nome=nome,
                descricao=context["descricao"] or None,
                criado_por=request.user,
            )

            # === Etapas em ordem: o browser envia na ordem atual do DOM ===
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

            # === Definições de Propriedades do Pipeline ===
            # Observação: se 'opcoes' for JSONField, convertemos "A;B;C" -> ["A","B","C"].
            # Se você optou por TextField, pode salvar a string "A;B;C" direto.
            defs_to_create = []
            for p in props_postadas:
                nome_p = p["nome"].strip()
                if not nome_p:
                    continue

                tipo_p = p["tipo"] or "text"
                obrig_p = bool(p["obrigatorio"])

                # ordem
                try:
                    ordem_p = int(p["ordem"])
                except Exception:
                    ordem_p = len(defs_to_create)

                # opções
                opcoes_raw = p["opcoes"] or ""
                opcoes_list = [o.strip() for o in opcoes_raw.split(";") if o.strip()] or None

                # Se o campo opcoes for JSONField: passe a lista; se for TextField, passe a string:
                # -> Ajuste UMA das linhas abaixo conforme seu model:
                defs_to_create.append(PipelinePropriedade(
                    pipeline=pipeline,
                    nome=nome_p,
                    tipo=tipo_p,
                    obrigatorio=obrig_p,
                    ordem=ordem_p,
                    opcoes=opcoes_list,            # JSONField
                    # opcoes=opcoes_raw or None,   # TextField (se você usou TextField)
                    valor_padrao=p["valor_padrao"] or None,
                ))

            if defs_to_create:
                PipelinePropriedade.objects.bulk_create(defs_to_create)

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
@require_http_methods(["GET", "POST"])
@transaction.atomic
def pipeline_edit(request, pk):
    filtro = {"pk": pk}
    if hasattr(Pipeline, "criado_por"):
        filtro["criado_por"] = request.user
    pipeline = get_object_or_404(Pipeline, **filtro)

    if request.method == "POST":
        # --- base ---
        nome = (request.POST.get("nome") or "").strip()
        descricao = (request.POST.get("descricao") or "").strip() or None

        if not nome:
            messages.error(request, "Nome é obrigatório.")
            return _render_edit(request, pipeline, nome=nome, descricao=descricao)

        pipeline.nome = nome
        pipeline.descricao = descricao
        pipeline.save()

        # -------------------------
        # ETAPAS (CRUD + ordenação)
        # -------------------------
        s_ids   = request.POST.getlist("etapas-id")      # hidden
        s_nomes = request.POST.getlist("etapas-nome")
        s_stats = request.POST.getlist("etapas-status")

        existing_stage_ids = set(pipeline.etapas.values_list("id", flat=True))
        posted_stage_ids   = set(int(x) for x in s_ids if x.isdigit())
        # deletar etapas removidas do form
        to_delete = existing_stage_ids - posted_stage_ids
        if to_delete:
            pipeline.etapas.filter(id__in=to_delete).delete()

        pos = 10
        for i in range(len(s_nomes)):
            sid   = s_ids[i] if i < len(s_ids) else ""
            nomei = (s_nomes[i] or "").strip()
            if not nomei:
                # linha vazia (ou marcada para remover no UI)
                continue
            status_i = (s_stats[i] if i < len(s_stats) and s_stats[i] else "ABERTO").strip()

            if sid and sid.isdigit():
                # update
                etapa = Etapa.objects.get(id=int(sid))
                etapa.nome = nomei
                etapa.status = status_i
                etapa.posicao = pos
                etapa.save(update_fields=["nome", "status", "posicao"])
                # garante vínculo (para o caso de etapas não vinculadas)
                pipeline.etapas.add(etapa)
            else:
                # create
                etapa = Etapa.objects.create(
                    nome=nomei, status=status_i, posicao=pos,
                    criado_por=getattr(request, "user", None)
                )
                pipeline.etapas.add(etapa)
            pos += 10

        # ----------------------------------------
        # PROPRIEDADES DO PIPELINE (CRUD + ordem)
        # ----------------------------------------
        p_ids    = request.POST.getlist("prop_id")
        p_nomes  = request.POST.getlist("prop_nome")
        p_tipos  = request.POST.getlist("prop_tipo")
        p_obr    = request.POST.getlist("prop_obrigatorio")
        p_opcoes = request.POST.getlist("prop_opcoes")        # "A;B;C" ou JSONField -> tratamos abaixo
        p_defs   = request.POST.getlist("prop_valor_padrao")
        p_ordem  = request.POST.getlist("prop_ordem")
        p_grupo  = request.POST.getlist("prop_grupo") if "prop_grupo" in request.POST else []

        existing_prop_ids = set(pipeline.propriedades_def.values_list("id", flat=True))
        posted_prop_ids   = set(int(x) for x in p_ids if x.isdigit())
        # deletar defs removidas
        to_delete_defs = existing_prop_ids - posted_prop_ids
        if to_delete_defs:
            pipeline.propriedades_def.filter(id__in=to_delete_defs).delete()

        # iremos coletar as defs recém-criadas para backfill
        new_defs = []

        for i in range(len(p_nomes)):
            nomep = (p_nomes[i] or "").strip()
            if not nomep:
                continue

            tid   = p_ids[i] if i < len(p_ids) else ""
            tipo  = (p_tipos[i] if i < len(p_tipos) else "text") or "text"
            obrig = (p_obr[i] == "on") if i < len(p_obr) else False
            vpad  = (p_defs[i] if i < len(p_defs) else "") or None
            try:
                ordem = int(p_ordem[i])
            except Exception:
                ordem = i
            grupo = ((p_grupo[i] if i < len(p_grupo) else "") or None)

            # trata opções (JSONField OU TextField)
            op_raw  = (p_opcoes[i] if i < len(p_opcoes) else "") or ""
            op_list = [o.strip() for o in op_raw.split(";") if o.strip()] or None

            if tid and tid.isdigit():
                # update
                d = PipelinePropriedade.objects.get(id=int(tid), pipeline=pipeline)
                d.nome = nomep
                d.tipo = tipo
                d.obrigatorio = obrig
                d.ordem = ordem
                # se seu model tem 'grupo'
                if hasattr(d, "grupo"):
                    d.grupo = grupo
                # JSONField:
                if hasattr(d, "opcoes"):
                    d.opcoes = op_list
                d.valor_padrao = vpad
                d.save()
            else:
                # create
                d = PipelinePropriedade.objects.create(
                    pipeline=pipeline,
                    nome=nomep,
                    tipo=tipo,
                    obrigatorio=obrig,
                    ordem=ordem,
                    valor_padrao=vpad,
                    **({"grupo": grupo} if "grupo" in PipelinePropriedade._meta.fields_map or hasattr(PipelinePropriedade, "grupo") else {})
                )
                # JSONField:
                if hasattr(d, "opcoes"):
                    d.opcoes = op_list
                    d.save(update_fields=["opcoes"])
                new_defs.append(d)

        # -------------------------------
        # Backfill das NOVAS definições
        # -------------------------------
        if new_defs:
            cards = list(pipeline.cards.all().only("id"))
            if cards:
                existing = set(
                    Propriedade.objects
                    .filter(card__in=cards, definicao__in=new_defs)
                    .values_list("card_id", "definicao_id")
                )
                to_create = []
                for c in cards:
                    for d in new_defs:
                        if (c.id, d.id) not in existing:
                            to_create.append(Propriedade(card_id=c.id, definicao_id=d.id, valor=d.valor_padrao))
                if to_create:
                    Propriedade.objects.bulk_create(to_create, batch_size=500)

        messages.success(request, "Pipeline atualizado com sucesso.")
        return redirect("kanban:pipeline_detail", pipeline_id=pipeline.pk)

    # GET
    return _render_edit(request, pipeline)


def _render_edit(request, pipeline, nome=None, descricao=None):
    context = {
        "is_edit": True,
        "pipeline": pipeline,
        "nome": nome if nome is not None else pipeline.nome,
        "descricao": descricao if descricao is not None else (pipeline.descricao or ""),
        "statuses": STATUS_ETAPA,
        "TIPOS_PROPRIEDADE": TIPOS_PROPRIEDADE,
        # para as tabelas:
        "etapas": pipeline.etapas.order_by("posicao", "id"),
        "props": pipeline.propriedades_def.order_by("ordem", "id"),
    }
    return render(request, "kanban/pipeline_edit.html", context)

def pipeline_create_prop_row(request):
    html = render_to_string("kanban/partials/pipeline_prop_row.html", {
        "TIPOS_PROPRIEDADE": TIPOS_PROPRIEDADE,
        "preset": {},
    })
    return HttpResponse(html)

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

def _card_qs_with_props():
    return (
        Card.objects
        .select_related("etapa", "pipeline", "criado_por")
        .prefetch_related(
            "tarefas",
            Prefetch(
                "propriedades",
                queryset=Propriedade.objects
                    .select_related("definicao")
                    .order_by("definicao__ordem", "definicao__id")
            )
        )
    )

@login_required
def card_detail(request, card_id):
    """HTML do corpo do drawer (partial)."""
    card = get_object_or_404(_card_qs_with_props(), id=card_id)
    total = card.tarefas.count()
    done = card.tarefas.filter(concluido=True).count()
    ctx = {"card": card, "total": total, "done": done}
    return render(request, "kanban/partials/card_drawer.html", ctx)

@require_http_methods(["POST"])
@login_required
def card_props_update(request, card_id):
    """Salva os valores das propriedades vinda do drawer."""
    card = get_object_or_404(_card_qs_with_props(), id=card_id)
    props = list(card.propriedades.select_related("definicao"))
    for p in props:
        field = f"prop_{p.definicao_id}"
        if field in request.POST:
            val = request.POST.get(field)
            if p.definicao.tipo == "bool":
                val = "true" if request.POST.get(field) in ("on","true","1") else "false"
            p.valor = val or None
    Propriedade.objects.bulk_update(props, ["valor"])
    # re-renderiza o drawer já atualizado
    total = card.tarefas.count()
    done = card.tarefas.filter(concluido=True).count()
    return render(request, "kanban/partials/card_drawer.html", {"card": card, "total": total, "done": done})

@login_required
def ticket_detail(request, card_id):
    """Tela cheia do ticket (página completa)."""
    card = get_object_or_404(_card_qs_with_props(), id=card_id)
    total = card.tarefas.count()
    done = card.tarefas.filter(concluido=True).count()
    return render(request, "kanban/ticket_detail.html", {"card": card, "total": total, "done": done})

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
# kanban_templates/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from urllib.parse import urlencode
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date
from collections import defaultdict
from django.db.models import Q
from kanban.models import Pipeline
from .models import PipelineTemplate
from .services import build_template_json_from_pipeline  # ou serialize_pipeline/padrão que você adotou

@login_required
@require_POST
def template_from_pipeline(request, pipeline_id):
    # se você usa dono do pipeline, restringe ao criador
    filtro = {"id": pipeline_id}
    if hasattr(Pipeline, "criado_por"):
        filtro["criado_por"] = request.user

    pipeline = get_object_or_404(Pipeline, **filtro)

    nome = (request.POST.get("nome") or f"Template de {pipeline.nome}").strip()
    descricao = (request.POST.get("descricao") or pipeline.descricao or "").strip() or None
    vis = request.POST.get("visibilidade") or "private"
    if vis not in ("private", "org", "public"):
        vis = "private"

    doc = build_template_json_from_pipeline(pipeline)

    tpl = PipelineTemplate.objects.create(
        nome=nome,
        descricao=descricao,
        doc=doc,
        visibilidade=vis,
        criado_por=request.user,
    )

    # Para HTMX: você pode redirecionar ou só devolver um 204 e fechar o modal no front
    resp = HttpResponse(status=204)
    resp["HX-Redirect"] = reverse("kanban:pipeline_detail", kwargs={"pipeline_id": pipeline.id})
    # ^ redireciona de volta pro detail (ou troque para uma página de templates, se tiver)
    return resp


@login_required
def template_list(request):
    qs = PipelineTemplate.objects.select_related("criado_por").filter(
        Q(criado_por=request.user) | Q(visibilidade="public")
    )

    # ------- filtros -------
    criado_por = request.GET.get("criado_por")  # "me" ou user_id
    if criado_por:
        if criado_por == "me":
            qs = qs.filter(criado_por=request.user)
        else:
            try:
                qs = qs.filter(criado_por_id=int(criado_por))
            except ValueError:
                pass

    de = request.GET.get("de")   # YYYY-MM-DD
    ate = request.GET.get("ate")
    if de:
        d = parse_date(de)
        if d:
            qs = qs.filter(criado_em__date__gte=d)
    if ate:
        d = parse_date(ate)
        if d:
            qs = qs.filter(criado_em__date__lte=d)

    ordenar = request.GET.get("ordenar", "recentes")
    order_map = {
        "recentes": "-criado_em",
        "antigos": "criado_em",
        "az": "nome",
        "za": "-nome",
    }
    qs = qs.order_by(order_map.get(ordenar, "-criado_em"))

    # ------- computa contadores por template (rápido e seguro) -------
    templates = []
    for t in qs:
        doc = t.doc or {}
        t.count_etapas = len(doc.get("etapas") or [])
        t.count_props = len(doc.get("propriedades") or [])
        t.count_checklists = len(doc.get("checklists") or [])
        templates.append(t)

    # ------- paginação -------
    paginator = Paginator(templates, 12)  # 12 cards por página
    page_obj = paginator.get_page(request.GET.get("page"))

    # lista de autores para o filtro
    creators = (PipelineTemplate.objects.select_related("criado_por")
                .values("criado_por_id", "criado_por__username")
                .distinct().order_by("criado_por__username"))

    # preserva querystring (sem page) para paginação/links
    params = request.GET.copy()
    params.pop("page", None)
    base_qs = urlencode(params, doseq=True)

    context = {
        "page_obj": page_obj,
        "creators": creators,
        "current": {
            "criado_por": criado_por or "",
            "de": de or "",
            "ate": ate or "",
            "ordenar": ordenar,
        },
        "base_qs": base_qs,
    }
    return render(request, "kanban_templates/template_list.html", context)

def _ord(e, i):
    # fallback se não houver posicao
    return int(e.get("posicao") or (i + 1) * 10)

@login_required
def template_detail(request, tpl_id):
    tpl = get_object_or_404(PipelineTemplate, id=tpl_id)
    doc = tpl.doc or {}

    raw_steps = doc.get("etapas") or []
    steps = sorted(
        [
            {
                "key": s.get("key") or f"e{i+1}",
                "nome": s.get("nome") or f"Etapa {i+1}",
                "descricao": s.get("descricao"),
                "posicao": _ord(s, i),
                "status": s.get("status") or "ABERTO",
            }
            for i, s in enumerate(raw_steps)
        ],
        key=lambda s: s["posicao"],
    )

    props = doc.get("propriedades") or []
    checklists = doc.get("checklists") or []

    # separa checklists do pipeline e por etapa
    pipe_cls = []
    step_cls_map = defaultdict(list)
    for s in steps:
        s["checklists"] = step_cls_map.get(s["key"], [])
    for cl in checklists:
        alvo = cl.get("alvo") or {}
        alvo_tipo = alvo.get("tipo") or "pipeline"
        item_count = len(cl.get("itens") or [])
        info = {
            "nome": cl.get("nome") or "Checklist",
            "descricao": cl.get("descricao"),
            "ordem": int(cl.get("ordem") or 0),
            "itens": cl.get("itens") or [],
            "itens_count": item_count,
        }
        if alvo_tipo == "etapa":
            step_cls_map[alvo.get("ref")].append(info)
        else:
            pipe_cls.append(info)

    # ordena checklists
    pipe_cls.sort(key=lambda x: (x["ordem"], x["nome"]))
    for k in step_cls_map:
        step_cls_map[k].sort(key=lambda x: (x["ordem"], x["nome"]))

    # métricas rápidas
    meta = {
        "steps": len(steps),
        "props": len(props),
        "checklists": len(checklists),
        "items": sum(len(cl.get("itens") or []) for cl in checklists),
    }

    return render(
        request,
        "kanban_templates/template_detail.html",
        {
            "tpl": tpl,
            "steps": steps,
            "props": props,
            "pipe_cls": pipe_cls,
            "step_cls_map": dict(step_cls_map),
            "meta": meta,
        },
    )

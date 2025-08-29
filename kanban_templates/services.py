# kanban_templates/services.py
from typing import Dict, Any, List
from django.db import transaction
from django.db.models import Q

from kanban.models import (
    Pipeline, Etapa, PipelinePropriedade,
    Checklist, ChecklistItem,
)
from .models import PipelineTemplate


def build_template_json_from_pipeline(pipeline: Pipeline) -> Dict[str, Any]:
    etapas = list(
        pipeline.etapas.order_by("posicao", "id")
        .values("id", "nome", "descricao", "posicao", "status")
    )

    key_by_etapa_id: Dict[int, str] = {}
    etapas_json: List[Dict[str, Any]] = []
    for i, e in enumerate(etapas, start=1):
        key = f"e{i}"
        key_by_etapa_id[e["id"]] = key
        etapas_json.append({
            "key": key,
            "nome": e["nome"],
            "descricao": e.get("descricao"),
            "posicao": e.get("posicao") or i * 10,
            "status": e.get("status") or "ABERTO",
        })

    props_json: List[Dict[str, Any]] = []
    for p in pipeline.propriedades_def.order_by("ordem", "id"):
        props_json.append({
            "nome": p.nome,
            "tipo": p.tipo,
            "ordem": p.ordem,
            "obrigatorio": p.obrigatorio,
            "opcoes": p.opcoes or [],
            "valor_padrao": p.valor_padrao,
        })

    # IMPORTANTE: incluir checklists do pipeline E das etapas do pipeline
    checklists = (
        Checklist.objects
        .filter(Q(pipeline=pipeline) | Q(etapa__in=pipeline.etapas.all()))
        .select_related("pipeline", "etapa")
        .prefetch_related("itens")
        .order_by("ordem", "id")
    )

    cls_json: List[Dict[str, Any]] = []
    for cl in checklists:
        alvo = {"tipo": "pipeline"} if cl.etapa_id is None else {
            "tipo": "etapa",
            "ref": key_by_etapa_id.get(cl.etapa_id),
        }
        itens = [
            {
                "titulo": it.titulo,
                "descricao": it.descricao,
                "ordem": it.ordem,
                "obrigatorio": it.obrigatorio,
                "prazo_dias": it.prazo_dias,
            }
            for it in cl.itens.all().order_by("ordem", "id")
        ]
        cls_json.append({
            "nome": cl.nome,
            "descricao": cl.descricao,
            "ordem": cl.ordem,
            "alvo": alvo,
            "itens": itens,
        })

    return {
        "etapas": etapas_json,
        "propriedades": props_json,
        "checklists": cls_json,
    }


def exportar_pipeline_para_template(pipeline: Pipeline, user) -> PipelineTemplate:
    doc = build_template_json_from_pipeline(pipeline)
    return PipelineTemplate.objects.create(
        nome=f"Template de {pipeline.nome}",
        descricao=pipeline.descricao,
        doc=doc,
        criado_por=user,
    )


@transaction.atomic
def instanciar_template(template: PipelineTemplate, dono) -> Pipeline:
    doc = template.doc or {}
    etapas_doc = doc.get("etapas", [])
    props_doc = doc.get("propriedades", [])
    cls_doc = doc.get("checklists", [])

    pipeline = Pipeline.objects.create(
        nome=template.nome,
        descricao=template.descricao,
        criado_por=dono,
    )

    # Etapas
    etapa_map: Dict[str, Etapa] = {}
    pos = 10
    for e in etapas_doc:
        posicao = int(e.get("posicao") or pos)
        et = Etapa.objects.create(
            nome=e["nome"],
            descricao=e.get("descricao") or None,
            posicao=posicao,
            status=e.get("status") or "ABERTO",
            criado_por=dono,
        )
        pipeline.etapas.add(et)
        etapa_map[e.get("key") or f"e{posicao // 10}"] = et
        pos = posicao + 10

    # Propriedades
    defs: List[PipelinePropriedade] = []
    for i, p in enumerate(props_doc):
        defs.append(PipelinePropriedade(
            pipeline=pipeline,
            nome=p["nome"],
            tipo=p.get("tipo") or "text",
            obrigatorio=bool(p.get("obrigatorio")),
            ordem=int(p.get("ordem") if p.get("ordem") is not None else i),
            opcoes=p.get("opcoes") or [],
            valor_padrao=p.get("valor_padrao"),
        ))
    if defs:
        PipelinePropriedade.objects.bulk_create(defs)

    # Checklists
    for cl in cls_doc:
        alvo = cl.get("alvo") or {"tipo": "pipeline"}
        etapa = None
        if alvo.get("tipo") == "etapa":
            etapa = etapa_map.get(alvo.get("ref"))

        checklist = Checklist.objects.create(
            nome=cl["nome"],
            descricao=cl.get("descricao") or None,
            ordem=int(cl.get("ordem") or 0),
            pipeline=pipeline if etapa is None else None,
            etapa=etapa,
            criado_por=dono,
        )

        itens_to_create: List[ChecklistItem] = []
        for j, it in enumerate(cl.get("itens", [])):
            itens_to_create.append(ChecklistItem(
                checklist=checklist,
                titulo=it["titulo"],
                descricao=it.get("descricao") or None,
                obrigatorio=bool(it.get("obrigatorio")),
                ordem=int(it.get("ordem") if it.get("ordem") is not None else j),
                prazo_dias=it.get("prazo_dias"),
            ))
        if itens_to_create:
            ChecklistItem.objects.bulk_create(itens_to_create)

    return pipeline

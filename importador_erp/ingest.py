# app/services/ingest_contratos.py
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.utils.timezone import make_naive
from .models import ContratoLocacao, Cliente  # ajuste o import conforme seu app
from clientes.models import ClienteLicense  # ajuste conforme seu app
from .constantes import mapa_tipos_imovel, mapa_tipos_contrato, mapa_categoricos, mapa_garantias, mapa_aluguel_garantido, SEXO_MAP
from typing import Iterable, List
import re

# --------- helpers mínimos ---------
def _parse_date(s: str | None):
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None  # se vier em outro formato, ignore

def _parse_decimal(s: str | None, default=None):
    if s in (None, ""):
        return default
    try:
        return Decimal(str(s))
    except Exception:
        return default

def _from_map(m: dict, key, default=""):
    return m.get(str(key), default)

def _to_bool(v) -> bool:
    return str(v).strip() not in ("", "0", "False", "false", "None", "null")

def _upsert_cliente(nome: str | None, documento: str | None):
    """
    Tenta identificar por documento; se não houver, usa nome.
    Ajuste os campos de Cliente conforme seu modelo (ex.: cpf_cnpj/documento).
    """
    nome = (nome or "").strip() or "Sem nome"
    if documento:
        obj, _ = Cliente.objects.get_or_create(documento=documento, defaults={"nome": nome})
        if obj.nome != nome:
            obj.nome = nome
            obj.save(update_fields=["nome"])
        return obj
    obj, _ = Cliente.objects.get_or_create(nome=nome)
    return obj

# --------- mapeamento e persistência ---------
def salvar_contrato(item: dict, licenca: ClienteLicense) -> ContratoLocacao:
    ident = int(item["id_contrato_con"])

    contrato, _ = ContratoLocacao.objects.update_or_create(
        licenca=licenca,                           # <<--- usa a FK aqui
        identificador_contrato=ident,
        defaults={
            "nome_do_imovel": item.get("st_imovel_imo") or item.get("st_endereco_imo") or "",
            "data_inicio": _parse_date(item.get("dt_inicio_con")),
            "data_fim": _parse_date(item.get("dt_fim_con")),
            "aluguel_garantido": _to_bool(item.get("nm_repassegarantido_con") or item.get("fl_tiporepassegarantido_con")),
            "tipo_garantia": _from_map(mapa_garantias, item.get("fl_garantia_con")),
            "data_inicio_garantia": _parse_date(item.get("dt_garantiainicio_con")),
            "data_fim_garantia": _parse_date(item.get("dt_garantiafim_con")),
            "data_inicio_seguro_incendio": _parse_date(item.get("dt_seguroincendioinicio_con")),
            "data_fim_seguro_incendio": _parse_date(item.get("dt_seguroincendiofim_con")),
            "data_ultimo_reajuste": _parse_date(item.get("dt_ultimoreajuste_con")),
            "valor_aluguel": _parse_decimal(item.get("vl_aluguel_con"), Decimal("0")),
            "taxa_administracao": _parse_decimal(item.get("tx_adm_con"), Decimal("0")),
            "taxa_locacao": _parse_decimal(item.get("tx_locacao_con"), Decimal("0")),
            "valor_venda_imovel": _parse_decimal(item.get("vl_venda_imo")),
            "valor_garantia_parcela": _parse_decimal(item.get("vl_garantiaparcela_con")),
            "valor_seguro_incendio": _parse_decimal(item.get("vl_seguroincendio_con")),
            "tipo_imovel": _from_map(mapa_tipos_imovel, item.get("st_tipo_imo")),
            "tipo_contrato": _from_map(mapa_tipos_contrato, item.get("id_tipo_con")),
            "status_contrato": _from_map(mapa_categoricos, item.get("fl_status_con")),
            "contrato_ativo": _to_bool(item.get("fl_ativo_con")),
            "renovacao_automatica": _to_bool(item.get("fl_renovacaoautomatica_con")),
        },
    )

    proprietarios = [
        _upsert_cliente(p.get("st_nome_pes") or p.get("st_fantasia_pes"), p.get("st_cnpj_pes"))
        for p in item.get("proprietarios_beneficiarios", [])
    ]
    inquilinos = [
        _upsert_cliente(i.get("st_nomeinquilino") or i.get("st_fantasia_pes"), i.get("st_cnpj_pes"))
        for i in item.get("inquilinos", [])
    ]

    contrato.proprietarios.set(proprietarios or [])
    contrato.inquilinos.set(inquilinos or [])
    return contrato

@transaction.atomic
def salvar_contratos(itens: list[dict], licenca: ClienteLicense) -> list[ContratoLocacao]:
    return [salvar_contrato(item, licenca) for item in itens]


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")

def _sexo(v: str | None) -> str:
    return SEXO_MAP.get(str(v or "").strip(), "I")  # fallback simples

def _email_or_placeholder(email: str | None, ident: int) -> str:
    email = (email or "").strip()
    return email if email else f"noemail-{ident}@invalid.local"

@transaction.atomic
def salvar_proprietarios(proprietarios: Iterable[dict]) -> List[Cliente]:
    """
    Recebe a lista item['proprietarios_beneficiarios'] do JSON e
    retorna a lista de objetos Cliente (PROPRIETARIO) salvos/atualizados.
    """
    salvos: list[Cliente] = []

    for p in proprietarios or []:
        # chave única do Superlógica
        ident_str = p.get("id_pessoa_pes") or p.get("id_proprietario_pes")
        if not ident_str:
            # sem identificador não dá pra manter consistência — pula
            continue
        ident = int(str(ident_str))

        nome = (p.get("st_nome_pes") or p.get("st_fantasia_pes") or "").strip() or "Sem nome"
        cpf_cnpj = _digits(p.get("st_cnpj_pes"))
        rg = (p.get("st_rg_pes") or "").strip()
        sexo = _sexo(p.get("st_sexo_pes"))
        email = _email_or_placeholder(p.get("st_email_pes"), ident)
        telefone = _digits(p.get("st_celular_pes") or p.get("st_telefone_pes"))

        obj, created = Cliente.objects.get_or_create(
            identificador_pessoa=ident,
            defaults=dict(
                cpf_cnpj=cpf_cnpj,
                rg=rg,
                sexo=sexo,
                nome=nome,
                email=email,
                telefone=telefone,
                tipo="PROPRIETARIO",
            ),
        )

        # se já existia, atualiza campos voláteis
        if not created:
            changed = False
            for field, value in [
                ("cpf_cnpj", cpf_cnpj),
                ("rg", rg),
                ("sexo", sexo),
                ("nome", nome),
                ("email", email),
                ("telefone", telefone),
                ("tipo", "PROPRIETARIO"),  # garante o tipo correto
            ]:
                if getattr(obj, field) != value and value not in (None, ""):
                    setattr(obj, field, value)
                    changed = True
            if changed:
                obj.save()

        salvos.append(obj)

    return salvos
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


def _email_placeholder(nome: str, ident: str | int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (nome or "").lower()).strip("-") or "sem-nome"
    return f"noemail-{base}-{ident}@invalid.local"

def _ident_from(d: dict) -> int | None:
    # cobre variações comuns de chaves nos payloads
    for k in [
        "id_pessoa_pes",
        "id_proprietario_pes",
        "id_inquilino_pes",
        "id_pessoa",
        "id_cliente_pes",
        "id_pessoainquilino_pes",
    ]:
        v = d.get(k)
        if v not in (None, "", 0, "0"):
            try:
                return int(str(v))
            except Exception:
                pass
    return None

def _upsert_cliente(nome: str | None, documento: str | None, tipo: str, ident_pessoa: int | None) -> Cliente:
    """
    Usa 'identificador_pessoa' (ID do Superlógica) como chave principal.
    'cpf_cnpj' é mantido/atualizado como dado secundário.
    """
    if not ident_pessoa:
        # Sem ID não dá pra garantir unicidade → melhor pular ou logar
        # Você pode levantar uma exceção específica se preferir.
        raise ValueError("ident_pessoa ausente para cliente")

    nome = (nome or "").strip() or "Sem nome"
    cpf_cnpj = _digits(documento)
    ident_para_email = str(ident_pessoa)

    defaults = dict(
        identificador_pessoa=ident_pessoa,
        cpf_cnpj=cpf_cnpj,
        rg="",
        sexo="I",
        nome=nome,
        email=_email_placeholder(nome, ident_para_email),
        telefone="",
        tipo=tipo,
    )

    obj, created = Cliente.objects.get_or_create(
        identificador_pessoa=ident_pessoa,
        defaults=defaults,
    )

    # atualizações mínimas sem sobrescrever à toa
    changed = False
    if cpf_cnpj and obj.cpf_cnpj != cpf_cnpj:
        obj.cpf_cnpj = cpf_cnpj; changed = True
    if obj.nome != nome:
        obj.nome = nome; changed = True
    if obj.tipo != tipo:
        obj.tipo = tipo; changed = True
    if changed:
        obj.save(update_fields=["cpf_cnpj", "nome", "tipo"])

    return obj

# --------- mapeamento e persistência ---------
def salvar_contrato(item: dict, licenca: ClienteLicense) -> ContratoLocacao:
    ident = int(item["id_contrato_con"])

    contrato, _ = ContratoLocacao.objects.update_or_create(
        licenca=licenca,
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

    proprietarios = []
    for p in item.get("proprietarios_beneficiarios", []):
        ident_pessoa = _ident_from(p)
        proprietarios.append(
            _upsert_cliente(
                p.get("st_nome_pes") or p.get("st_fantasia_pes"),
                p.get("st_cnpj_pes"),
                tipo="PROPRIETARIO",
                ident_pessoa=ident_pessoa,
            )
        )

    inquilinos = []
    for i in item.get("inquilinos", []):
        ident_pessoa = _ident_from(i)
        inquilinos.append(
            _upsert_cliente(
                i.get("st_nomeinquilino") or i.get("st_fantasia_pes"),
                i.get("st_cnpj_pes"),
                tipo="INQUILINO",
                ident_pessoa=ident_pessoa,
            )
        )

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
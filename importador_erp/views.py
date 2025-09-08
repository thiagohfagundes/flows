# integrador/views.py
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from clientes.models import ClienteLicense
from integrador.models import LicenseIntegration
import requests
from django.conf import settings
from .ingest import salvar_contratos, salvar_proprietarios

from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.db.models import Q, Count, Sum, ExpressionWrapper, Value, Case, When, IntegerField, F
from django.db.models.functions import Now
from django.shortcuts import render
from .models import Cliente, ContratoLocacao  # ajuste o import conforme seu app
from django.db.models.functions import Coalesce
from django.db.models import DecimalField


@login_required
def importar_contratos_meus(request):
    pessoa = getattr(request.user, "pessoa", None)
    if not pessoa:
        return HttpResponseBadRequest("Usuário sem Pessoa vinculada")
    licencas = pessoa.licencas.all()

    if not licencas:
        return HttpResponseNotFound("Usuário sem Licença vinculada")
    else:
        integ = LicenseIntegration.objects.get(license_id=licencas[0].id, is_active=True)
        token = integ.access_token
        print(token)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "app_token": settings.INTEGRADOR_APP_TOKEN,   # do .env
            "access_token": token,      # do banco (decrypt automático)
        }

        todos_contratos = []
        pagina = 1

        while True:
            url = f"http://apps.superlogica.net/imobiliaria/api/contratos?pagina={pagina}&itensPorPagina=50"
            response = requests.get(url, headers=headers).json()

            if response['data'] != []:
                todos_contratos.extend(response['data'])
                pagina += 1
            else:
                break

        salvar_contratos(todos_contratos, licencas[0])

    return JsonResponse({"licencas": [licenca.license_name for licenca in licencas], "contratos": todos_contratos})

def importar_proprietarios(request):
    pessoa = getattr(request.user, "pessoa", None)
    if not pessoa:
        return HttpResponseBadRequest("Usuário sem Pessoa vinculada")

    lic = pessoa.licencas.select_related("integracao").first()
    if not lic or not getattr(lic, "integracao", None) or not lic.integracao.is_active:
        return HttpResponseNotFound("Licença sem integração ativa")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "app_token": settings.INTEGRADOR_APP_TOKEN,
        "access_token": lic.integracao.access_token,  # já vem descriptografado
    }

    todos = []
    pagina = 1
    base = settings.IMOBILIARIAS_BASE_URL  # ex.: "https://apps.superlogica.net/imobiliaria/api"
    while True:
            url = f"http://apps.superlogica.net/imobiliaria/api/proprietarios?pagina={pagina}&itensPorPagina=50"
            response = requests.get(url, headers=headers).json()

            if response['data'] != []:
                todos.extend(response['data'])
                pagina += 1
            else:
                break
    
    print(todos)
    proprietarios = salvar_proprietarios(todos)
    return JsonResponse({"ok": True, "license_name": lic.license_name, "importados": len(proprietarios)})

@method_decorator(login_required, name="dispatch")
class MeusClientesListView(ListView):
    model = Cliente
    template_name = "importador_erp/clientes_lista.html"
    context_object_name = "clientes"
    paginate_by = 12

    def get_queryset(self):
        # Zero tipado como Decimal
        ZERO_DEC = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))

        qs = (
            Cliente.objects.all()
            .annotate(
                contratos_inq=Count("contratos_inquilino", distinct=True),
                contratos_prop=Count("contratos_proprietario", distinct=True),
                total_aluguel_inq=Coalesce(Sum("contratos_inquilino__valor_aluguel"), ZERO_DEC),
                total_aluguel_prop=Coalesce(Sum("contratos_proprietario__valor_aluguel"), ZERO_DEC),
            )
        )

        # total_aluguel = total_inq + total_prop (com output_field decimal)
        qs = qs.annotate(
            total_aluguel=ExpressionWrapper(
                Coalesce(Sum("contratos_inquilino__valor_aluguel"), ZERO_DEC)
                + Coalesce(Sum("contratos_proprietario__valor_aluguel"), ZERO_DEC),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

        g = self.request.GET

        # Busca textual
        q = g.get("q")
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(email__icontains=q)
                | Q(cpf_cnpj__icontains=q)
                | Q(telefone__icontains=q)
            )

        # Tipo de cliente
        tipo = g.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        # Vínculo
        vinculo = g.get("vinculo")  # 'prop' | 'inq' | 'semcontrato'
        if vinculo == "prop":
            qs = qs.filter(contratos_proprietario__isnull=False)
        elif vinculo == "inq":
            qs = qs.filter(contratos_inquilino__isnull=False)
        elif vinculo == "semcontrato":
            qs = qs.filter(
                contratos_proprietario__isnull=True,
                contratos_inquilino__isnull=True,
            )

        # Ativo (em qualquer contrato vinculado)
        ativo = g.get("ativo")  # '1' ou '0'
        if ativo in ("1", "0"):
            flag = ativo == "1"
            qs = qs.filter(
                Q(contratos_inquilino__contrato_ativo=flag)
                | Q(contratos_proprietario__contrato_ativo=flag)
            )

        # Status do contrato
        status_contrato = g.get("status")
        if status_contrato:
            qs = qs.filter(
                Q(contratos_inquilino__status_contrato=status_contrato)
                | Q(contratos_proprietario__status_contrato=status_contrato)
            )

        # Faixa de aluguel
        min_aluguel = g.get("min_aluguel")
        max_aluguel = g.get("max_aluguel")
        if min_aluguel:
            qs = qs.filter(
                Q(contratos_inquilino__valor_aluguel__gte=min_aluguel)
                | Q(contratos_proprietario__valor_aluguel__gte=min_aluguel)
            )
        if max_aluguel:
            qs = qs.filter(
                Q(contratos_inquilino__valor_aluguel__lte=max_aluguel)
                | Q(contratos_proprietario__valor_aluguel__lte=max_aluguel)
            )

        # Período de início do contrato
        dt_ini = g.get("dt_ini")
        dt_fim = g.get("dt_fim")
        if dt_ini:
            qs = qs.filter(
                Q(contratos_inquilino__data_inicio__gte=dt_ini)
                | Q(contratos_proprietario__data_inicio__gte=dt_ini)
            )
        if dt_fim:
            qs = qs.filter(
                Q(contratos_inquilino__data_inicio__lte=dt_fim)
                | Q(contratos_proprietario__data_inicio__lte=dt_fim)
            )

        # Ordenação
        ordenar = g.get("ordenar", "nome")
        if ordenar in ("nome", "-nome"):
            qs = qs.order_by(ordenar)
        elif ordenar == "contratos":
            qs = qs.order_by("contratos_inq", "contratos_prop", "nome")
        elif ordenar == "-contratos":
            qs = qs.order_by("-contratos_inq", "-contratos_prop", "nome")
        elif ordenar == "aluguel":
            qs = qs.order_by("total_aluguel")
        elif ordenar == "-aluguel":
            qs = qs.order_by("-total_aluguel")
        else:
            qs = qs.order_by("nome")

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy()
        qs.pop("page", None)
        ctx["querystring"] = qs.urlencode()
        # Se quiser popular o select de tipos dinamicamente:
        ctx["choices_tipo"] = getattr(self.model, "TIPOS_CLIENTE_LOCACAO", None)
        return ctx

@method_decorator(login_required, name="dispatch")
class ContratosLocacaoListView(ListView):
    model = ContratoLocacao
    template_name = "importador_erp/contratos_lista.html"
    context_object_name = "contratos"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            ContratoLocacao.objects.all()
            .annotate(
                num_inquilinos=Count("inquilinos", distinct=True),
                num_proprietarios=Count("proprietarios", distinct=True),
                # situação calculada em tempo de execução a partir das datas
                situacao=Case(
                    When(data_fim__lt=Now(), then=Value(0)),          # Vencido
                    When(data_inicio__gt=Now(), then=Value(2)),       # Futuro
                    default=Value(1),                                 # Vigente
                    output_field=IntegerField(),
                )
            )
        )

        g = self.request.GET

        # Busca textual (imóvel, id contrato, status, tipo, cliente relacionado)
        q = g.get("q")
        if q:
            qs = qs.filter(
                Q(nome_do_imovel__icontains=q)
                | Q(identificador_contrato__icontains=q)
                | Q(status_contrato__icontains=q)
                | Q(tipo_imovel__icontains=q)
                | Q(tipo_contrato__icontains=q)
                | Q(inquilinos__nome__icontains=q)
                | Q(proprietarios__nome__icontains=q)
                | Q(inquilinos__email__icontains=q)
                | Q(proprietarios__email__icontains=q)
                | Q(inquilinos__cpf_cnpj__icontains=q)
                | Q(proprietarios__cpf_cnpj__icontains=q)
            )

        # Ativo
        ativo = g.get("ativo")  # '1' ou '0'
        if ativo in ("1", "0"):
            qs = qs.filter(contrato_ativo=(ativo == "1"))

        # Situação (calculada): vencido|vigente|futuro
        sit = g.get("situacao")
        if sit == "vencido":
            qs = qs.filter(data_fim__lt=Now())
        elif sit == "vigente":
            qs = qs.filter(data_fim__gte=Now(), data_inicio__lte=Now())
        elif sit == "futuro":
            qs = qs.filter(data_inicio__gt=Now())

        # Aluguel garantido
        alg_gar = g.get("aluguel_garantido")  # '1' | '0'
        if alg_gar in ("1", "0"):
            qs = qs.filter(aluguel_garantido=(alg_gar == "1"))

        # Tipo de garantia (texto livre)
        tipo_garantia = g.get("tipo_garantia")
        if tipo_garantia:
            qs = qs.filter(tipo_garantia__icontains=tipo_garantia)

        # Renovação automática
        renov = g.get("renovacao")  # '1' | '0'
        if renov in ("1", "0"):
            qs = qs.filter(renovacao_automatica=(renov == "1"))

        # Tipo de imóvel / tipo de contrato / status
        tipo_imovel = g.get("tipo_imovel")
        if tipo_imovel:
            qs = qs.filter(tipo_imovel__icontains=tipo_imovel)

        tipo_contrato = g.get("tipo_contrato")
        if tipo_contrato:
            qs = qs.filter(tipo_contrato__icontains=tipo_contrato)

        status_contrato = g.get("status")
        if status_contrato:
            qs = qs.filter(status_contrato__icontains=status_contrato)

        # Faixa de aluguel
        min_aluguel = g.get("min_aluguel")
        max_aluguel = g.get("max_aluguel")
        if min_aluguel:
            qs = qs.filter(valor_aluguel__gte=min_aluguel)
        if max_aluguel:
            qs = qs.filter(valor_aluguel__lte=max_aluguel)

        # Intervalo de datas
        ini_de = g.get("ini_de")   # data_inicio >= ini_de
        ini_ate = g.get("ini_ate") # data_inicio <= ini_ate
        fim_de = g.get("fim_de")   # data_fim >= fim_de
        fim_ate = g.get("fim_ate") # data_fim <= fim_ate

        if ini_de:
            qs = qs.filter(data_inicio__gte=ini_de)
        if ini_ate:
            qs = qs.filter(data_inicio__lte=ini_ate)
        if fim_de:
            qs = qs.filter(data_fim__gte=fim_de)
        if fim_ate:
            qs = qs.filter(data_fim__lte=fim_ate)

        # Papel do cliente filtrando por nome (ex.: apenas contratos onde "João" é inquilino)
        inq_nome = g.get("inq")
        if inq_nome:
            qs = qs.filter(inquilinos__nome__icontains=inq_nome)

        prop_nome = g.get("prop")
        if prop_nome:
            qs = qs.filter(proprietarios__nome__icontains=prop_nome)

        # Ordenação
        ordenar = g.get("ordenar", "-data_inicio")
        if ordenar in ("data_inicio", "-data_inicio", "data_fim", "-data_fim",
                       "valor_aluguel", "-valor_aluguel", "nome_do_imovel", "-nome_do_imovel"):
            qs = qs.order_by(ordenar)
        elif ordenar in ("situacao", "-situacao"):
            qs = qs.order_by(ordenar)
        else:
            qs = qs.order_by("-data_inicio")

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy()
        qs.pop("page", None)
        ctx["querystring"] = qs.urlencode()
        return ctx
from decimal import Decimal
import re
import unicodedata

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.models import Usuario
from approvals.models import Alocacao, Associacao
from approvals.services import anular_associacao, aprovar_candidata, reprovar_nota
from diagnostics.models import Diagnostico, TarefaProcessamento
from files.models import Arquivo
from invoices.models import NotaFiscal
from invoices.services import import_nfe_xml
from matching.models import Conferencia, ConferenciaCandidata
from matching.services import recalcular_conferencia_para_nota
from orders.models import Pedido
from orders.services import import_coral_order_spreadsheet
from organizations.models import EmpresaCliente, Fornecedor, Loja
from audit.models import EventoAuditoria
from reports.models import Exportacao
from receiving.models import OcorrenciaRecebimento, Recebimento
from receiving.services import (
    alerta_30_dias,
    anular_recebimento,
    confirmar_recebimento,
    dias_aguardando_recebimento,
)


MENU = [
    ("dashboard", "Dashboard", "ui:dashboard"),
    ("fila", "Fila", "ui:fila"),
    ("recebimento", "Recebimento", "ui:recebimento"),
    ("planilhas", "Planilhas", "ui:planilhas"),
    ("relatorios", "Relatorios", "ui:relatorios"),
    ("diagnostico", "Diagnostico", "ui:diagnostico"),
    ("configuracoes", "Configuracoes", "ui:configuracoes"),
    ("sobre", "Sobre", "ui:sobre"),
]

ADMIN_MENU_KEYS = {"diagnostico", "configuracoes"}


def menu_for_user(user):
    if user and user.is_authenticated and not user.pode_administrar():
        return [item for item in MENU if item[0] not in ADMIN_MENU_KEYS]
    return MENU


def base_context(active: str, user=None) -> dict:
    return {
        "active": active,
        "menu": menu_for_user(user),
        "empresa_nome": "Destiny In",
        "loja_nome": "Matriz",
        "can_admin": bool(user and user.is_authenticated and user.pode_administrar()),
    }


def scoped_companies(user):
    if user.is_mestre:
        return EmpresaCliente.objects.filter(ativa=True)
    if user.empresa_cliente_id:
        return EmpresaCliente.objects.filter(id=user.empresa_cliente_id, ativa=True)
    return EmpresaCliente.objects.none()


def scoped_stores(user):
    return user.lojas_autorizadas()


def scoped_suppliers(user):
    companies = scoped_companies(user)
    return Fornecedor.objects.filter(empresa_cliente__in=companies, ativo=True)


def _normalize_lookup_value(value) -> str:
    text = "" if value is None else str(value).strip()
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", without_accents.upper())).strip()


def _compact_lookup_value(value) -> str:
    return re.sub(r"[^A-Z0-9]+", "", _normalize_lookup_value(value))


def _matches_lookup(filename: str, *candidates) -> bool:
    filename_normalized = _normalize_lookup_value(filename)
    filename_compact = _compact_lookup_value(filename)
    filename_tokens = set(filename_normalized.split())
    for candidate in candidates:
        candidate_normalized = _normalize_lookup_value(candidate)
        candidate_compact = _compact_lookup_value(candidate)
        if len(candidate_compact) < 3:
            continue
        if candidate_normalized in filename_normalized or candidate_compact in filename_compact:
            return True
        candidate_tokens = [token for token in candidate_normalized.split() if len(token) >= 3]
        if candidate_tokens and all(token in filename_tokens for token in candidate_tokens):
            return True
    return False


def _single_item(queryset):
    items = list(queryset[:2])
    return items[0] if len(items) == 1 else None


def _infer_from_filename(filename: str, queryset, fields: tuple[str, ...]):
    matches = []
    for item in queryset:
        if _matches_lookup(filename, *(getattr(item, field, "") for field in fields)):
            matches.append(item)
    if len(matches) == 1:
        return matches[0], ""
    if len(matches) > 1:
        return None, "ambigua"
    return None, "ausente"


def resolve_spreadsheet_context(user, filename: str, empresa_id: str, loja_id: str, fornecedor_id: str):
    errors = []
    companies = scoped_companies(user)
    all_stores = scoped_stores(user)
    all_suppliers = scoped_suppliers(user)

    empresa = companies.filter(id=empresa_id).first() if empresa_id else None
    loja = all_stores.filter(id=loja_id).first() if loja_id else None
    fornecedor = all_suppliers.filter(id=fornecedor_id).first() if fornecedor_id else None

    if empresa_id and not empresa:
        errors.append("empresa selecionada nao esta disponivel para este usuario")
    if loja_id and not loja:
        errors.append("loja selecionada nao esta disponivel para este usuario")
    if fornecedor_id and not fornecedor:
        errors.append("fornecedor selecionado nao esta disponivel para este usuario")

    empresa_status = ""
    if not empresa:
        empresa = _single_item(companies)
    if not empresa:
        empresa, empresa_status = _infer_from_filename(filename, companies, ("nome", "codigo", "cnpj_normalizado"))
    store_scope = all_stores.filter(empresa_cliente=empresa) if empresa else all_stores
    supplier_scope = all_suppliers.filter(empresa_cliente=empresa) if empresa else all_suppliers

    loja_status = ""
    if not loja:
        loja = _single_item(store_scope)
    if not loja:
        loja, loja_status = _infer_from_filename(filename, store_scope, ("nome", "codigo", "cnpj_normalizado"))
    if not empresa and loja:
        empresa = loja.empresa_cliente
        supplier_scope = all_suppliers.filter(empresa_cliente=empresa)

    fornecedor_status = ""
    if not fornecedor:
        fornecedor = _single_item(supplier_scope)
    if not fornecedor:
        fornecedor, fornecedor_status = _infer_from_filename(filename, supplier_scope, ("nome", "cnpj_normalizado"))
    if not empresa and fornecedor:
        empresa = fornecedor.empresa_cliente
        store_scope = all_stores.filter(empresa_cliente=empresa)

    if empresa and not loja:
        loja = _single_item(store_scope)
    if empresa and not loja:
        loja, loja_status = _infer_from_filename(filename, store_scope, ("nome", "codigo", "cnpj_normalizado"))

    if loja and empresa and loja.empresa_cliente_id != empresa.id:
        errors.append("loja identificada pertence a outra empresa")
    if fornecedor and empresa and fornecedor.empresa_cliente_id != empresa.id:
        errors.append("fornecedor identificado pertence a outra empresa")

    if not empresa:
        errors.append("empresa ambigua" if empresa_status == "ambigua" else "empresa")
    if not loja:
        errors.append("loja ambigua" if loja_status == "ambigua" else "loja")
    if not fornecedor:
        errors.append("fornecedor ambiguo" if fornecedor_status == "ambigua" else "fornecedor")

    if errors:
        return None, None, None, ", ".join(errors)
    return empresa, loja, fornecedor, ""


def scoped_invoices(user):
    invoices = NotaFiscal.objects.filter(empresa_cliente__in=scoped_companies(user))
    if user.is_visualizador:
        invoices = invoices.filter(loja__in=scoped_stores(user))
    return invoices.exclude(status_conferencia=NotaFiscal.StatusConferencia.REJEITADA)


def user_can_access_file(user, arquivo: Arquivo) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_mestre:
        return True
    if user.empresa_cliente_id != arquivo.empresa_cliente_id:
        return False
    if user.pode_administrar():
        return True
    if hasattr(arquivo, "nota_fiscal") and arquivo.nota_fiscal.loja_id:
        return scoped_stores(user).filter(id=arquivo.nota_fiscal.loja_id).exists()
    if hasattr(arquivo, "pedido") and arquivo.pedido.loja_id:
        return scoped_stores(user).filter(id=arquivo.pedido.loja_id).exists()
    if hasattr(arquivo, "exportacao") and arquivo.exportacao.associacao_id:
        return scoped_stores(user).filter(id=arquivo.exportacao.associacao.pedido.loja_id).exists()
    return False


@login_required
def dashboard(request):
    companies = scoped_companies(request.user)
    pedidos = Pedido.objects.filter(empresa_cliente__in=companies, removido=False)
    if request.user.is_visualizador:
        pedidos = pedidos.filter(loja__in=scoped_stores(request.user))

    notas = scoped_invoices(request.user)
    notas_fila = notas.filter(status_conferencia=NotaFiscal.StatusConferencia.AGUARDANDO_APROVACAO)
    recebimento_count = notas.filter(
        status_conferencia=NotaFiscal.StatusConferencia.APROVADA,
        status_recebimento=NotaFiscal.StatusRecebimento.AGUARDANDO_RECEBIMENTO,
    ).count()
    diagnosticos_count = (
        Diagnostico.objects.filter(empresa_cliente__in=companies, status=Diagnostico.Status.ABERTO).count()
        if request.user.pode_administrar()
        else 0
    )

    fila_prioritaria = []
    for nota in notas_fila.select_related("fornecedor", "loja").order_by("criada_em")[:8]:
        candidata = (
            ConferenciaCandidata.objects.filter(conferencia__nota_fiscal=nota, conferencia__vigente=True)
            .select_related("pedido")
            .first()
        )
        alertas = candidata.alertas if candidata else []
        fila_prioritaria.append(
            {
                "numero": f"{nota.numero}/{nota.serie}",
                "fornecedor": nota.fornecedor.nome,
                "loja": nota.loja.nome if nota.loja else "Loja em revisao",
                "pedido": str(candidata.pedido) if candidata else "Sem candidata",
                "compatibilidade": f"{candidata.compatibilidade}%" if candidata else "0.00%",
                "alerta": ", ".join(alertas[:2]) if alertas else nota.get_situacao_fila_display(),
                "nivel": candidata.get_nivel_display() if candidata else "Pendente",
                "tom": candidata.nivel.lower() if candidata else "baixa",
            }
        )

    eventos = EventoAuditoria.objects.filter(empresa_cliente__in=companies).select_related("usuario")[:8]
    atividade_lista = list(eventos)
    atividade_resumo = {
        "total": len(atividade_lista),
        "ultima": atividade_lista[0] if atividade_lista else None,
    }
    metrics = [
        {
            "label": "NFs na fila",
            "value": str(notas_fila.count()),
            "tone": "warning",
            "detail": "Aguardando decisao administrativa",
            "url": "ui:fila",
        },
        {
            "label": "Pedidos ativos",
            "value": str(pedidos.count()),
            "tone": "neutral",
            "detail": "Com saldo ou historico operacional",
            "url": "ui:planilhas",
        },
        {
            "label": "Aguardando recebimento",
            "value": str(recebimento_count),
            "tone": "info",
            "detail": "NFs aprovadas ainda nao recebidas",
            "url": "ui:recebimento",
        },
    ]
    if request.user.pode_administrar():
        metrics.append(
            {
                "label": "Diagnosticos abertos",
                "value": str(diagnosticos_count),
                "tone": "danger",
                "detail": "Falhas tecnicas para revisao",
                "url": "ui:diagnostico",
            }
        )

    context = base_context("dashboard", request.user)
    context.update(
        {
            "metrics": metrics,
            "fila_prioritaria": fila_prioritaria,
            "atividade": atividade_lista,
            "atividade_resumo": atividade_resumo,
        }
    )
    return render(request, "ui/dashboard.html", context)


@login_required
def fila(request):
    if request.method == "POST":
        if not request.user.pode_administrar():
            raise PermissionDenied("Somente Administrador ou Mestre executa acoes na Fila.")

        action = request.POST.get("action", "import_xml")
        if action == "approve":
            candidata = ConferenciaCandidata.objects.filter(id=request.POST.get("candidata_id")).first()
            if not candidata:
                messages.error(request, "Candidata nao encontrada.")
            else:
                try:
                    aprovar_candidata(
                        candidata=candidata,
                        usuario=request.user,
                        justificativa=request.POST.get("justificativa", ""),
                    )
                    messages.success(request, "Associacao aprovada e saldos atualizados.")
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect("ui:fila")

        if action == "reject":
            nota = NotaFiscal.objects.filter(id=request.POST.get("nota_fiscal_id")).first()
            if not nota:
                messages.error(request, "NF nao encontrada.")
            else:
                try:
                    reprovar_nota(
                        nota_fiscal=nota,
                        usuario=request.user,
                        justificativa=request.POST.get("justificativa", ""),
                    )
                    messages.success(request, "NF reprovada e removida da Fila.")
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect("ui:fila")

        if action == "annul":
            associacao = Associacao.objects.filter(id=request.POST.get("associacao_id")).first()
            if not associacao:
                messages.error(request, "Associacao nao encontrada.")
            else:
                try:
                    anular_associacao(
                        associacao=associacao,
                        usuario=request.user,
                        justificativa=request.POST.get("justificativa", ""),
                    )
                    messages.success(request, "Associacao anulada e saldos restaurados.")
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect("ui:fila")

        empresa = _single_item(scoped_companies(request.user))
        uploads = request.FILES.getlist("xmls")
        if not empresa:
            messages.error(request, "Nao consegui identificar a empresa automaticamente para importar XML.")
            return redirect("ui:fila")
        if not uploads:
            messages.error(request, "Selecione pelo menos um XML.")
            return redirect("ui:fila")

        for uploaded_file in uploads:
            result = import_nfe_xml(
                empresa_cliente=empresa,
                uploaded_file=uploaded_file,
                usuario=request.user,
            )
            if result.duplicate:
                if result.nota_fiscal:
                    recalcular_conferencia_para_nota(result.nota_fiscal)
                messages.warning(request, f"{uploaded_file.name}: XML duplicado, nenhuma nova NF criada.")
            elif result.nota_fiscal:
                recalcular_conferencia_para_nota(result.nota_fiscal)
                messages.success(request, f"{uploaded_file.name}: NF-e importada com sucesso.")
            else:
                messages.error(request, f"{uploaded_file.name}: enviado para Diagnostico.")
        return redirect("ui:fila")

    notas_qs = scoped_invoices(request.user).select_related("fornecedor", "loja").prefetch_related("itens")
    fila_resumo = {
        "total": notas_qs.count(),
        "aguardando": notas_qs.filter(status_conferencia=NotaFiscal.StatusConferencia.AGUARDANDO_APROVACAO).count(),
        "aprovadas": notas_qs.filter(status_conferencia=NotaFiscal.StatusConferencia.APROVADA).count(),
        "anuladas": notas_qs.filter(status_conferencia=NotaFiscal.StatusConferencia.ANULADA).count(),
    }
    notas = list(notas_qs[:50])
    for nota in notas:
        nota.conferencia_vigente = (
            Conferencia.objects.filter(nota_fiscal=nota, vigente=True)
            .prefetch_related("candidatas")
            .first()
        )
        nota.candidata_principal = nota.conferencia_vigente.candidatas.first() if nota.conferencia_vigente else None
        nota.alertas_preview = nota.candidata_principal.alertas[:3] if nota.candidata_principal else []
        nota.nivel_tom = nota.candidata_principal.nivel.lower() if nota.candidata_principal else "baixa"
        nota.compat_percent = format(nota.candidata_principal.compatibilidade, "f") if nota.candidata_principal else "0"
        nota.aprovacao_exige_justificativa = bool(
            nota.candidata_principal
            and (
                nota.candidata_principal.alertas
                or nota.candidata_principal.compatibilidade < Decimal("100.00")
                or nota.candidata_principal.ambigua
            )
        )
        nota.status_tom = nota.status_conferencia.lower()
        nota.associacao_vigente = Associacao.objects.filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE).first()
        nota.exportacao_principal = (
            nota.associacao_vigente.exportacoes.select_related("arquivo").first()
            if nota.associacao_vigente
            else None
        )
        nota.detail_alternatives = (
            nota.conferencia_vigente.candidatas.exclude(id=nota.candidata_principal.id).select_related("pedido")[:5]
            if nota.conferencia_vigente and nota.candidata_principal
            else []
        )
        nota.detail_items = (
            nota.candidata_principal.itens.select_related("item_nota_fiscal", "item_pedido")
            if nota.candidata_principal
            else []
        )
    context = base_context("fila", request.user)
    context.update(
        {
            "notas": notas,
            "fila_resumo": fila_resumo,
            "empresas": scoped_companies(request.user),
            "can_import": request.user.pode_administrar(),
            "can_decide": request.user.pode_administrar(),
        }
    )
    return render(request, "ui/fila.html", context)


@login_required
def download_arquivo(request, arquivo_id):
    arquivo = get_object_or_404(Arquivo, pk=arquivo_id)
    if not user_can_access_file(request.user, arquivo):
        raise Http404()
    absolute_path = settings.NFCH_STORAGE_ROOT / arquivo.caminho_relativo
    if not absolute_path.exists():
        raise Http404()
    return FileResponse(
        absolute_path.open("rb"),
        as_attachment=True,
        filename=arquivo.nome_original,
        content_type=arquivo.mime_type or "application/octet-stream",
    )


@login_required
def recebimento(request):
    if request.method == "POST":
        if not request.user.pode_administrar():
            raise PermissionDenied("Somente Administrador ou Mestre confirma recebimento.")

        action = request.POST.get("action")
        if action in {"confirm", "confirm_divergence"}:
            nota = scoped_invoices(request.user).filter(id=request.POST.get("nota_fiscal_id")).first()
            data_recebimento = parse_date(request.POST.get("data_recebimento", ""))
            if not nota:
                messages.error(request, "NF nao encontrada para recebimento.")
            else:
                try:
                    confirmar_recebimento(
                        nota_fiscal=nota,
                        usuario=request.user,
                        data_recebimento=data_recebimento,
                        com_divergencia=action == "confirm_divergence",
                        ocorrencia_tipo=request.POST.get("ocorrencia_tipo", ""),
                        ocorrencia_descricao=request.POST.get("ocorrencia_descricao", ""),
                    )
                    messages.success(request, "Recebimento confirmado.")
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect("ui:recebimento")

        if action == "annul_receiving":
            rec = (
                Recebimento.objects.filter(id=request.POST.get("recebimento_id"), empresa_cliente__in=scoped_companies(request.user))
                .select_related("nota_fiscal")
                .first()
            )
            if not rec:
                messages.error(request, "Recebimento nao encontrado.")
            else:
                try:
                    anular_recebimento(
                        recebimento=rec,
                        usuario=request.user,
                        justificativa=request.POST.get("justificativa", ""),
                    )
                    messages.success(request, "Recebimento anulado e quantidades retornaram para faturado.")
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect("ui:recebimento")

    pendentes = list(
        scoped_invoices(request.user)
        .filter(
            status_conferencia=NotaFiscal.StatusConferencia.APROVADA,
            status_recebimento=NotaFiscal.StatusRecebimento.AGUARDANDO_RECEBIMENTO,
            associacoes__status=Associacao.Status.VIGENTE,
        )
        .select_related("fornecedor", "loja")
        .distinct()[:50]
    )
    for nota in pendentes:
        nota.dias_aguardando = dias_aguardando_recebimento(nota)
        nota.alerta_recebimento = alerta_30_dias(nota)
        nota.recebimento_tom = "warning" if nota.alerta_recebimento else "info"
        nota.associacao_vigente = Associacao.objects.filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE).first()

    historico = Recebimento.objects.filter(empresa_cliente__in=scoped_companies(request.user)).select_related(
        "nota_fiscal",
        "nota_fiscal__fornecedor",
        "nota_fiscal__loja",
        "confirmado_por",
    ).prefetch_related("ocorrencias")
    if request.user.is_visualizador:
        historico = historico.filter(nota_fiscal__loja__in=scoped_stores(request.user))

    historico_resumo = historico.aggregate(
        recebidos_vigentes=Count("id", filter=Q(status=Recebimento.Status.VIGENTE)),
        recebidos_com_divergencia=Count(
            "id",
            filter=Q(status=Recebimento.Status.VIGENTE, resultado=Recebimento.Resultado.COM_DIVERGENCIA),
        ),
    )
    recebimento_resumo = {
        "pendentes": len(pendentes),
        "alertas_30": sum(1 for nota in pendentes if nota.alerta_recebimento),
        "recebidos_vigentes": historico_resumo["recebidos_vigentes"],
        "recebidos_com_divergencia": historico_resumo["recebidos_com_divergencia"],
    }

    context = base_context("recebimento", request.user)
    context.update(
        {
            "pendentes": pendentes,
            "historico": historico[:50],
            "recebimento_resumo": recebimento_resumo,
            "hoje": timezone.localdate(),
            "ocorrencia_tipos": OcorrenciaRecebimento.Tipo.choices,
            "can_decide": request.user.pode_administrar(),
        }
    )
    return render(request, "ui/recebimento.html", context)


@login_required
def planilhas(request):
    if request.method == "POST":
        if not request.user.pode_administrar():
            raise PermissionDenied("Somente Administrador ou Mestre importa planilhas.")

        uploads = request.FILES.getlist("planilhas")

        if not uploads:
            messages.error(request, "Selecione pelo menos uma planilha.")
            return redirect("ui:planilhas")

        for uploaded_file in uploads:
            empresa, loja, fornecedor, context_error = resolve_spreadsheet_context(
                request.user,
                uploaded_file.name,
                request.POST.get("empresa_cliente", ""),
                request.POST.get("loja", ""),
                request.POST.get("fornecedor", ""),
            )
            if context_error:
                messages.error(
                    request,
                    f"{uploaded_file.name}: nao consegui identificar automaticamente ({context_error}). "
                    "Confira o cadastro, o nome do arquivo ou use os campos opcionais para resolver ambiguidade.",
                )
                continue

            result = import_coral_order_spreadsheet(
                empresa_cliente=empresa,
                loja=loja,
                fornecedor=fornecedor,
                uploaded_file=uploaded_file,
                usuario=request.user,
            )
            if result.duplicate:
                messages.warning(request, f"{uploaded_file.name}: arquivo duplicado, nenhum novo pedido criado.")
            elif result.pedido:
                for nota in NotaFiscal.objects.filter(
                    empresa_cliente=empresa,
                    loja=loja,
                    fornecedor=fornecedor,
                    status_conferencia=NotaFiscal.StatusConferencia.AGUARDANDO_APROVACAO,
                ):
                    recalcular_conferencia_para_nota(nota)
                messages.success(
                    request,
                    f"{uploaded_file.name}: pedido importado com sucesso para {loja.nome} / {fornecedor.nome}.",
                )
            else:
                messages.error(request, f"{uploaded_file.name}: enviado para Diagnostico.")
        return redirect("ui:planilhas")

    decimal_zero = Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=3))
    pedidos_base = Pedido.objects.filter(empresa_cliente__in=scoped_companies(request.user), removido=False)
    if request.user.is_visualizador:
        pedidos_base = pedidos_base.filter(loja__in=scoped_stores(request.user))

    pedidos = (
        pedidos_base.select_related("arquivo", "fornecedor", "loja")
        .annotate(
            total_itens=Count("itens"),
            quantidade_total=Coalesce(Sum("itens__quantidade_pedida"), decimal_zero),
            saldo_total=Coalesce(Sum("itens__saldo_cache"), decimal_zero),
            faturado_total=Coalesce(Sum("itens__faturado_cache"), decimal_zero),
            recebido_total=Coalesce(Sum("itens__recebido_cache"), decimal_zero),
        )
    )
    resumo = pedidos_base.aggregate(
        pedidos_total=Count("id", distinct=True),
        itens_total=Count("itens"),
        saldo_total=Coalesce(Sum("itens__saldo_cache"), decimal_zero),
        faturado_total=Coalesce(Sum("itens__faturado_cache"), decimal_zero),
    )
    context = base_context("planilhas", request.user)
    context.update(
        {
            "planilhas": pedidos,
            "resumo": resumo,
            "empresas": scoped_companies(request.user),
            "lojas": scoped_stores(request.user),
            "fornecedores": scoped_suppliers(request.user),
            "can_import": request.user.pode_administrar(),
        }
    )
    return render(request, "ui/planilhas.html", context)


@login_required
def relatorios(request):
    companies = scoped_companies(request.user)
    stores = scoped_stores(request.user)
    notas = scoped_invoices(request.user)
    alocacoes = Alocacao.objects.filter(
        empresa_cliente__in=companies,
        status=Alocacao.Status.VIGENTE,
        associacao__status=Associacao.Status.VIGENTE,
    ).select_related(
        "associacao",
        "associacao__nota_fiscal",
        "associacao__pedido",
        "item_nota_fiscal",
        "item_pedido",
        "item_pedido__pedido",
        "item_pedido__pedido__loja",
        "item_pedido__pedido__fornecedor",
    )
    exportacoes = Exportacao.objects.filter(empresa_cliente__in=companies).select_related(
        "arquivo",
        "associacao",
        "associacao__pedido",
        "associacao__nota_fiscal",
    )
    if request.user.is_visualizador:
        alocacoes = alocacoes.filter(item_pedido__pedido__loja__in=stores)
        exportacoes = exportacoes.filter(associacao__pedido__loja__in=stores)
        eventos = EventoAuditoria.objects.none()
    else:
        eventos = EventoAuditoria.objects.filter(empresa_cliente__in=companies).select_related("usuario")

    relatorio_decimal_zero = Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=4))
    alocacao_resumo = alocacoes.aggregate(
        linhas_faturadas=Count("id"),
        quantidade_faturada=Coalesce(Sum("quantidade"), relatorio_decimal_zero),
        notas_faturadas=Count("associacao__nota_fiscal", distinct=True),
        pedidos_associados=Count("associacao__pedido", distinct=True),
    )
    recebimentos_vigentes = Recebimento.objects.filter(
        empresa_cliente__in=companies,
        status=Recebimento.Status.VIGENTE,
    )
    if request.user.is_visualizador:
        recebimentos_vigentes = recebimentos_vigentes.filter(nota_fiscal__loja__in=stores)

    context = base_context("relatorios", request.user)
    context.update(
        {
            "cards": [
                {
                    "titulo": "Historico",
                    "valor": f"{eventos.count()} eventos",
                    "detalhe": "Auditoria disponivel conforme permissao",
                },
                {
                    "titulo": "Itens faturados",
                    "valor": alocacao_resumo["linhas_faturadas"],
                    "detalhe": "Alocacoes aprovadas vigentes",
                },
                {
                    "titulo": "Quantidade faturada",
                    "valor": alocacao_resumo["quantidade_faturada"],
                    "detalhe": f"{alocacao_resumo['notas_faturadas']} NF(s) em {alocacao_resumo['pedidos_associados']} pedido(s)",
                },
                {
                    "titulo": "Exportacoes",
                    "valor": exportacoes.count(),
                    "detalhe": "Saidas autorizadas para download",
                },
            ],
            "linhas": eventos[:50],
            "alocacoes": alocacoes[:40],
            "exportacoes": exportacoes[:20],
            "notas": notas.select_related("fornecedor", "loja")[:20],
            "exportacoes_total": exportacoes.count(),
            "recebidos_total": recebimentos_vigentes.count(),
            "can_view_audit": not request.user.is_visualizador,
        }
    )
    return render(request, "ui/relatorios.html", context)


@login_required
def diagnostico(request):
    if not request.user.pode_administrar():
        raise PermissionDenied("Somente Administrador ou Mestre acessa Diagnostico.")

    companies = scoped_companies(request.user)
    diagnosticos_base = Diagnostico.objects.filter(empresa_cliente__in=companies).select_related("arquivo", "criado_por")
    tarefas = TarefaProcessamento.objects.filter(empresa_cliente__in=companies).select_related("arquivo")[:30]
    diagnostico_resumo = diagnosticos_base.aggregate(
        abertos=Count("id", filter=Q(status=Diagnostico.Status.ABERTO)),
        resolvidos=Count("id", filter=Q(status=Diagnostico.Status.RESOLVIDO)),
        erros=Count("id", filter=Q(severidade=Diagnostico.Severidade.ERRO)),
        alertas=Count("id", filter=Q(severidade=Diagnostico.Severidade.ALERTA)),
    )
    tarefa_resumo = TarefaProcessamento.objects.filter(empresa_cliente__in=companies).aggregate(
        aguardando=Count("id", filter=Q(estado=TarefaProcessamento.Estado.AGUARDANDO)),
        processando=Count("id", filter=Q(estado=TarefaProcessamento.Estado.PROCESSANDO)),
        erro=Count("id", filter=Q(estado=TarefaProcessamento.Estado.ERRO)),
    )
    context = base_context("diagnostico", request.user)
    context.update(
        {
            "diagnosticos": diagnosticos_base[:50],
            "diagnostico_resumo": diagnostico_resumo,
            "tarefas": tarefas,
            "tarefa_resumo": tarefa_resumo,
        }
    )
    return render(request, "ui/diagnostico.html", context)


@login_required
def configuracoes(request):
    if not request.user.pode_administrar():
        raise PermissionDenied("Somente Administrador ou Mestre acessa Configuracoes.")

    companies = scoped_companies(request.user)
    empresas = companies.annotate(
        total_lojas=Count("lojas", distinct=True),
        total_fornecedores=Count("fornecedores", distinct=True),
        total_usuarios=Count("usuarios", distinct=True),
    )
    lojas = Loja.objects.filter(empresa_cliente__in=companies).select_related("empresa_cliente")[:30]
    fornecedores = Fornecedor.objects.filter(empresa_cliente__in=companies).select_related("empresa_cliente")[:30]
    if request.user.is_mestre:
        usuarios_base = Usuario.objects.filter(
            Q(empresa_cliente__in=companies) | Q(role=Usuario.Role.MESTRE)
        ).select_related("empresa_cliente")
    else:
        usuarios_base = Usuario.objects.filter(empresa_cliente__in=companies).select_related("empresa_cliente")
    usuarios = usuarios_base[:30]

    configuracoes_resumo = {
        "empresas": empresas.count(),
        "lojas_ativas": Loja.objects.filter(empresa_cliente__in=companies, ativa=True).count(),
        "fornecedores_ativos": Fornecedor.objects.filter(empresa_cliente__in=companies, ativo=True).count(),
        "usuarios_ativos": usuarios_base.filter(is_active=True).count(),
    }
    context = base_context("configuracoes", request.user)
    context.update(
        {
            "empresas": empresas,
            "lojas": lojas,
            "fornecedores": fornecedores,
            "usuarios": usuarios,
            "configuracoes_resumo": configuracoes_resumo,
        }
    )
    return render(request, "ui/configuracoes.html", context)


@login_required
def sobre(request):
    context = base_context("sobre", request.user)
    context.update(
        {
            "versao": "Preview A10",
            "criador": "Kauan Gomes",
            "contato": "kauanalves.gomes14@gmail.com",
            "escopo": [
                "Rede interna",
                "Django e PostgreSQL",
                "Excel, XML NF-e modelo 55 e PDF opcional",
                "Aprovacao sempre administrativa",
            ],
            "modulos": [
                "Importacao de pedidos e NF-e",
                "Conferencia com candidatas e alertas",
                "Aprovacao administrativa com saldos",
                "Recebimento integral auditavel",
                "Relatorios e exportacoes autorizadas",
            ],
            "garantias": [
                "XML fiscal imutavel e permanente",
                "Banco como fonte operacional de verdade",
                "Saldo derivado de alocacoes aprovadas vigentes",
                "Eventos relevantes preservados em auditoria",
            ],
            "fora_mvp": [
                "Docker, Linux, nuvem ou acesso publico",
                "Aplicativo movel",
                "Inventario fisico",
                "Aprovacao automatica",
            ],
        }
    )
    return render(request, "ui/sobre.html", context)

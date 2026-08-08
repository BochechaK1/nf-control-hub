from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from approvals.models import Alocacao, Associacao
from approvals.services import atualizar_estado_pedido
from audit.models import EventoAuditoria
from audit.services import registrar_evento
from invoices.models import NotaFiscal
from orders.models import ItemPedido

from .models import OcorrenciaRecebimento, Recebimento


def require_admin(user):
    if not user or not user.pode_administrar():
        raise PermissionDenied("Somente Administrador ou Mestre pode confirmar recebimento.")


def q3(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def dias_aguardando_recebimento(nota: NotaFiscal, *, hoje=None) -> int:
    base = timezone.localtime(nota.data_emissao).date()
    current = hoje or timezone.localdate()
    return max((current - base).days, 0)


def alerta_30_dias(nota: NotaFiscal, *, hoje=None) -> bool:
    return dias_aguardando_recebimento(nota, hoje=hoje) >= 30


@transaction.atomic
def confirmar_recebimento(
    *,
    nota_fiscal: NotaFiscal,
    usuario,
    data_recebimento,
    com_divergencia: bool = False,
    ocorrencia_tipo: str = "",
    ocorrencia_descricao: str = "",
) -> Recebimento:
    require_admin(usuario)
    if data_recebimento is None:
        raise ValidationError("Data real do recebimento e obrigatoria.")
    if com_divergencia and (not ocorrencia_tipo or not ocorrencia_descricao.strip()):
        raise ValidationError("Recebimento com divergencia exige tipo e descricao da ocorrencia.")

    nota = NotaFiscal.objects.select_for_update().get(pk=nota_fiscal.pk)
    if nota.status_conferencia != NotaFiscal.StatusConferencia.APROVADA:
        raise ValidationError("Somente NF aprovada pode ser recebida.")
    if nota.status_recebimento != NotaFiscal.StatusRecebimento.AGUARDANDO_RECEBIMENTO:
        raise ValidationError("NF ja possui recebimento vigente.")
    if Recebimento.objects.filter(nota_fiscal=nota, status=Recebimento.Status.VIGENTE).exists():
        raise ValidationError("NF ja possui recebimento vigente.")

    associacao = (
        Associacao.objects.select_for_update()
        .filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE)
        .select_related("pedido")
        .first()
    )
    if not associacao:
        raise ValidationError("NF precisa de associacao vigente para ser recebida.")

    allocations = list(
        Alocacao.objects.select_for_update()
        .filter(associacao=associacao, status=Alocacao.Status.VIGENTE)
        .select_related("item_pedido")
    )
    if not allocations:
        raise ValidationError("NF aprovada sem alocacoes vigentes nao pode ser recebida.")

    locked_items = {
        item.id: item
        for item in ItemPedido.objects.select_for_update().filter(
            id__in=[allocation.item_pedido_id for allocation in allocations]
        )
    }
    for allocation in allocations:
        item = locked_items[allocation.item_pedido_id]
        quantidade = q3(allocation.quantidade)
        if item.faturado_cache < quantidade:
            raise ValidationError("Cache de faturado inconsistente; recebimento bloqueado.")
        item.faturado_cache = q3(item.faturado_cache - quantidade)
        item.recebido_cache = q3(item.recebido_cache + quantidade)
        item.clean()
        item.save(update_fields=["faturado_cache", "recebido_cache"])

    resultado = (
        Recebimento.Resultado.COM_DIVERGENCIA
        if com_divergencia
        else Recebimento.Resultado.SEM_DIVERGENCIA
    )
    recebimento = Recebimento.objects.create(
        empresa_cliente=nota.empresa_cliente,
        nota_fiscal=nota,
        resultado=resultado,
        data_recebimento=data_recebimento,
        confirmado_por=usuario,
    )
    ocorrencia = None
    if com_divergencia:
        ocorrencia = OcorrenciaRecebimento.objects.create(
            empresa_cliente=nota.empresa_cliente,
            recebimento=recebimento,
            nota_fiscal=nota,
            tipo=ocorrencia_tipo,
            descricao=ocorrencia_descricao.strip(),
            registrada_por=usuario,
        )

    nota.status_recebimento = (
        NotaFiscal.StatusRecebimento.RECEBIDA_COM_DIVERGENCIA
        if com_divergencia
        else NotaFiscal.StatusRecebimento.RECEBIDA_SEM_DIVERGENCIA
    )
    nota.save(update_fields=["status_recebimento"])
    atualizar_estado_pedido(associacao.pedido)
    registrar_evento(
        empresa_cliente=nota.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=recebimento,
        acao="RECEBIMENTO_CONFIRMADO",
        depois={
            "nota_fiscal_id": nota.id,
            "resultado": resultado,
            "data_recebimento": data_recebimento.isoformat(),
            "ocorrencia_id": ocorrencia.id if ocorrencia else None,
        },
    )
    return recebimento


@transaction.atomic
def anular_recebimento(*, recebimento: Recebimento, usuario, justificativa: str) -> Recebimento:
    require_admin(usuario)
    if not justificativa.strip():
        raise ValidationError("Anulacao de recebimento exige justificativa.")

    rec = (
        Recebimento.objects.select_for_update()
        .select_related("nota_fiscal")
        .get(pk=recebimento.pk)
    )
    if rec.status != Recebimento.Status.VIGENTE:
        raise ValidationError("Recebimento ja nao esta vigente.")

    nota = NotaFiscal.objects.select_for_update().get(pk=rec.nota_fiscal_id)
    associacao = (
        Associacao.objects.select_for_update()
        .filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE)
        .select_related("pedido")
        .first()
    )
    if not associacao:
        raise ValidationError("Recebimento sem associacao vigente nao pode ser anulado pelo fluxo comum.")

    allocations = list(
        Alocacao.objects.select_for_update()
        .filter(associacao=associacao, status=Alocacao.Status.VIGENTE)
        .select_related("item_pedido")
    )
    locked_items = {
        item.id: item
        for item in ItemPedido.objects.select_for_update().filter(
            id__in=[allocation.item_pedido_id for allocation in allocations]
        )
    }
    for allocation in allocations:
        item = locked_items[allocation.item_pedido_id]
        quantidade = q3(allocation.quantidade)
        if item.recebido_cache < quantidade:
            raise ValidationError("Cache de recebido inconsistente; anulacao bloqueada.")
        item.recebido_cache = q3(item.recebido_cache - quantidade)
        item.faturado_cache = q3(item.faturado_cache + quantidade)
        item.clean()
        item.save(update_fields=["faturado_cache", "recebido_cache"])

    rec.status = Recebimento.Status.ANULADO
    rec.anulada_por = usuario
    rec.anulada_em = timezone.now()
    rec.justificativa_anulacao = justificativa.strip()
    rec.save(update_fields=["status", "anulada_por", "anulada_em", "justificativa_anulacao"])

    nota.status_recebimento = NotaFiscal.StatusRecebimento.AGUARDANDO_RECEBIMENTO
    nota.save(update_fields=["status_recebimento"])
    atualizar_estado_pedido(associacao.pedido)
    registrar_evento(
        empresa_cliente=nota.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=rec,
        acao="RECEBIMENTO_ANULADO",
        motivo=justificativa.strip(),
        depois={"nota_fiscal_id": nota.id},
    )
    return rec

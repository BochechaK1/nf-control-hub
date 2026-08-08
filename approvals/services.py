from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from audit.models import EventoAuditoria
from audit.services import registrar_evento
from invoices.models import NotaFiscal
from matching.models import ConferenciaCandidata, ConferenciaItem
from orders.models import ItemPedido, Pedido

from .models import Alocacao, Associacao


def require_admin(user):
    if not user or not user.pode_administrar():
        raise PermissionDenied("Somente Administrador ou Mestre pode executar esta acao.")


def q4(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def atualizar_estado_pedido(pedido: Pedido) -> None:
    items = list(pedido.itens.all())
    has_saldo = any(item.saldo_cache > 0 for item in items)
    has_faturado = any(item.faturado_cache > 0 for item in items)
    has_recebido = any(item.recebido_cache > 0 for item in items)

    if has_saldo and not has_faturado and not has_recebido:
        estado = Pedido.Estado.ABERTA
    elif has_saldo and (has_faturado or has_recebido):
        estado = Pedido.Estado.PARCIALMENTE_FATURADA
    elif not has_saldo and has_faturado and has_recebido:
        estado = Pedido.Estado.PARCIALMENTE_RECEBIDA
    elif not has_saldo and has_faturado:
        estado = Pedido.Estado.FATURADA
    elif not has_saldo and has_recebido:
        estado = Pedido.Estado.CONCLUIDA
    else:
        estado = Pedido.Estado.ABERTA

    if pedido.estado != estado:
        pedido.estado = estado
        pedido.save(update_fields=["estado"])


def atualizar_estado_pedido_ids(ids) -> None:
    for pedido in Pedido.objects.filter(id__in=set(ids)):
        atualizar_estado_pedido(pedido)


@transaction.atomic
def aprovar_candidata(*, candidata: ConferenciaCandidata, usuario, justificativa: str = "") -> Associacao:
    require_admin(usuario)

    candidata = (
        ConferenciaCandidata.objects.select_related(
            "conferencia__nota_fiscal",
            "pedido",
            "conferencia__empresa_cliente",
        )
        .select_for_update()
        .get(pk=candidata.pk)
    )
    nota = NotaFiscal.objects.select_for_update().get(pk=candidata.conferencia.nota_fiscal_id)
    pedido = Pedido.objects.select_for_update().get(pk=candidata.pedido_id)

    if nota.status_fiscal == NotaFiscal.StatusFiscal.CANCELADA:
        raise ValidationError("NF cancelada nao pode ser aprovada.")
    if nota.status_conferencia != NotaFiscal.StatusConferencia.AGUARDANDO_APROVACAO:
        raise ValidationError("NF nao esta aguardando aprovacao.")
    if Associacao.objects.filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE).exists():
        raise ValidationError("NF ja possui associacao vigente.")
    if candidata.ambigua and not justificativa.strip():
        raise ValidationError("Candidata ambigua exige justificativa.")
    if (candidata.alertas or candidata.compatibilidade < Decimal("100.00")) and not justificativa.strip():
        raise ValidationError("Divergencia exige justificativa simples e objetiva.")

    confirmed_rows = list(
        candidata.itens.filter(resultado=ConferenciaItem.Resultado.CONFIRMADO)
        .select_related("item_pedido", "item_nota_fiscal")
        .order_by("ordem", "id")
    )
    if not confirmed_rows:
        raise ValidationError("Nao ha itens confirmados para alocar.")

    order_item_ids = [row.item_pedido_id for row in confirmed_rows if row.item_pedido_id]
    locked_items = {
        item.id: item
        for item in ItemPedido.objects.select_for_update().filter(id__in=order_item_ids)
    }

    associacao = Associacao.objects.create(
        empresa_cliente=nota.empresa_cliente,
        nota_fiscal=nota,
        pedido=pedido,
        candidata=candidata,
        aprovada_por=usuario,
        justificativa=justificativa.strip(),
    )

    alocacoes: list[Alocacao] = []
    for row in confirmed_rows:
        item = locked_items[row.item_pedido_id]
        saldo = q4(item.saldo_cache)
        quantidade_nf = q4(row.quantidade_nf)
        quantidade = min(saldo, quantidade_nf)
        if quantidade <= 0:
            raise ValidationError("Saldo mudou durante a aprovacao; recalcule a conferencia.")
        if quantidade > saldo:
            raise ValidationError("Aprovacao excederia o saldo do pedido.")

        item.saldo_cache = q4(saldo - quantidade)
        item.faturado_cache = q4(item.faturado_cache + quantidade)
        item.clean()
        item.save(update_fields=["saldo_cache", "faturado_cache"])
        alocacoes.append(
            Alocacao(
                empresa_cliente=nota.empresa_cliente,
                associacao=associacao,
                item_nota_fiscal=row.item_nota_fiscal,
                item_pedido=item,
                quantidade=quantidade,
            )
        )

    Alocacao.objects.bulk_create(alocacoes)
    nota.status_conferencia = NotaFiscal.StatusConferencia.APROVADA
    nota.save(update_fields=["status_conferencia"])
    atualizar_estado_pedido(pedido)
    registrar_evento(
        empresa_cliente=nota.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=associacao,
        acao="ASSOCIACAO_APROVADA",
        motivo=justificativa.strip(),
        depois={
            "nota_fiscal_id": nota.id,
            "pedido_id": str(pedido.id),
            "alocacoes": len(alocacoes),
            "quantidade_total": str(sum((item.quantidade for item in alocacoes), Decimal("0"))),
        },
    )
    from reports.services import gerar_copia_preenchida_associacao

    gerar_copia_preenchida_associacao(associacao=associacao, usuario=usuario)
    return associacao


@transaction.atomic
def reprovar_nota(*, nota_fiscal: NotaFiscal, usuario, justificativa: str) -> NotaFiscal:
    require_admin(usuario)
    if not justificativa.strip():
        raise ValidationError("Reprovacao exige justificativa.")

    nota = NotaFiscal.objects.select_for_update().get(pk=nota_fiscal.pk)
    if nota.status_conferencia != NotaFiscal.StatusConferencia.AGUARDANDO_APROVACAO:
        raise ValidationError("Somente NF aguardando aprovacao pode ser reprovada.")
    if Associacao.objects.filter(nota_fiscal=nota, status=Associacao.Status.VIGENTE).exists():
        raise ValidationError("NF com associacao vigente nao pode ser reprovada.")

    nota.status_conferencia = NotaFiscal.StatusConferencia.REJEITADA
    nota.save(update_fields=["status_conferencia"])
    registrar_evento(
        empresa_cliente=nota.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=nota,
        acao="NFE_REPROVADA",
        motivo=justificativa.strip(),
    )
    return nota


@transaction.atomic
def anular_associacao(*, associacao: Associacao, usuario, justificativa: str) -> Associacao:
    require_admin(usuario)
    if not justificativa.strip():
        raise ValidationError("Anulacao exige justificativa.")

    assoc = (
        Associacao.objects.select_for_update()
        .select_related("nota_fiscal", "pedido")
        .get(pk=associacao.pk)
    )
    if assoc.status != Associacao.Status.VIGENTE:
        raise ValidationError("Associacao ja nao esta vigente.")

    allocations = list(
        Alocacao.objects.select_for_update()
        .filter(associacao=assoc, status=Alocacao.Status.VIGENTE)
        .select_related("item_pedido")
    )
    order_item_ids = [allocation.item_pedido_id for allocation in allocations]
    locked_items = {
        item.id: item
        for item in ItemPedido.objects.select_for_update().filter(id__in=order_item_ids)
    }

    now = timezone.now()
    touched_orders = set()
    for allocation in allocations:
        item = locked_items[allocation.item_pedido_id]
        if item.faturado_cache < allocation.quantidade:
            raise ValidationError("Cache de faturado inconsistente; anulacao bloqueada.")
        item.faturado_cache = q4(item.faturado_cache - allocation.quantidade)
        item.saldo_cache = q4(item.saldo_cache + allocation.quantidade)
        item.clean()
        item.save(update_fields=["saldo_cache", "faturado_cache"])
        allocation.status = Alocacao.Status.ANULADA
        allocation.anulada_em = now
        allocation.save(update_fields=["status", "anulada_em"])
        touched_orders.add(item.pedido_id)

    assoc.status = Associacao.Status.ANULADA
    assoc.anulada_por = usuario
    assoc.anulada_em = now
    assoc.justificativa_anulacao = justificativa.strip()
    assoc.save(update_fields=["status", "anulada_por", "anulada_em", "justificativa_anulacao"])

    nota = assoc.nota_fiscal
    nota.status_conferencia = NotaFiscal.StatusConferencia.ANULADA
    nota.save(update_fields=["status_conferencia"])
    atualizar_estado_pedido_ids(touched_orders or {assoc.pedido_id})
    registrar_evento(
        empresa_cliente=assoc.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=assoc,
        acao="ASSOCIACAO_ANULADA",
        motivo=justificativa.strip(),
        depois={"alocacoes_anuladas": len(allocations)},
    )
    return assoc

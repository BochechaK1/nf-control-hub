from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher

from django.db import transaction

from invoices.models import ItemNotaFiscal, NotaFiscal
from orders.models import ItemPedido, Pedido

from .models import Conferencia, ConferenciaCandidata, ConferenciaItem


OPEN_ORDER_STATES = {
    Pedido.Estado.ABERTA,
    Pedido.Estado.PARCIALMENTE_FATURADA,
}

PERCENT = Decimal("100.00")


@dataclass
class CandidateScore:
    pedido: Pedido
    coverage_items: Decimal
    coverage_quantities: Decimal
    compatibility: Decimal
    level: str
    alerts: list[str]
    item_rows: list[dict]


def percent(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def level_for(compatibility: Decimal) -> str:
    if compatibility == PERCENT:
        return ConferenciaCandidata.Nivel.ALTA
    if compatibility >= Decimal("85.00"):
        return ConferenciaCandidata.Nivel.MEDIA
    return ConferenciaCandidata.Nivel.BAIXA


def text_similarity(left: str, right: str) -> Decimal:
    ratio = SequenceMatcher(None, left or "", right or "").ratio()
    return Decimal(str(ratio))


def candidate_orders_for_invoice(nota_fiscal: NotaFiscal):
    if not nota_fiscal.loja_id:
        return Pedido.objects.none()
    return (
        Pedido.objects.filter(
            empresa_cliente=nota_fiscal.empresa_cliente,
            loja=nota_fiscal.loja,
            fornecedor=nota_fiscal.fornecedor,
            estado__in=OPEN_ORDER_STATES,
            removido=False,
            itens__saldo_cache__gt=0,
        )
        .distinct()
        .order_by("data_operacional", "criado_em", "id")
    )


def best_text_suggestion(nf_item: ItemNotaFiscal, order_items: list[ItemPedido]) -> ItemPedido | None:
    best_item = None
    best_ratio = Decimal("0")
    for order_item in order_items:
        if order_item.codigo_normalizado:
            continue
        ratio = text_similarity(nf_item.descricao_normalizada, order_item.produto_normalizado)
        if ratio > best_ratio:
            best_ratio = ratio
            best_item = order_item
    if best_ratio >= Decimal("0.85"):
        return best_item
    return None


def score_candidate(nota_fiscal: NotaFiscal, pedido: Pedido) -> CandidateScore:
    nf_items = list(nota_fiscal.itens.all().order_by("numero_item"))
    order_items = list(pedido.itens.filter(saldo_cache__gt=0).order_by("linha", "id"))
    available_by_code: dict[str, list[ItemPedido]] = {}
    for item in order_items:
        if item.codigo_normalizado:
            available_by_code.setdefault(item.codigo_normalizado, []).append(item)

    confirmed_count = Decimal("0")
    quantity_coverages: list[Decimal] = []
    used_order_item_ids: set[int] = set()
    item_rows: list[dict] = []
    alerts: set[str] = set()

    for order, nf_item in enumerate(nf_items, start=1):
        matched_item = None
        if nf_item.codigo_normalizado:
            candidates = available_by_code.get(nf_item.codigo_normalizado, [])
            matched_item = next((item for item in candidates if item.id not in used_order_item_ids), None)

        if matched_item:
            used_order_item_ids.add(matched_item.id)
            confirmed_count += 1
            saldo = Decimal(matched_item.saldo_cache)
            quantity = Decimal(nf_item.quantidade)
            fits = min(saldo, quantity)
            excess = max(quantity - saldo, Decimal("0"))
            item_alerts: list[str] = []
            if quantity < saldo:
                alerts.add("PARCIALIDADE_LINHA")
                item_alerts.append("PARCIALIDADE_LINHA")
            if quantity > saldo:
                alerts.add("EXCESSO")
                item_alerts.append("EXCESSO")
            quantity_coverages.append(fits / quantity if quantity else Decimal("0"))
            item_rows.append(
                {
                    "item_nota_fiscal": nf_item,
                    "item_pedido": matched_item,
                    "resultado": ConferenciaItem.Resultado.CONFIRMADO,
                    "quantidade_nf": quantity,
                    "saldo_pedido": saldo,
                    "quantidade_cabe": fits,
                    "excesso": excess,
                    "alertas": item_alerts,
                    "observacao": "Codigo confirmado; descricao informativa.",
                    "ordem": order,
                }
            )
            continue

        suggestion = best_text_suggestion(nf_item, order_items)
        if suggestion:
            alerts.add("SUGESTAO_TEXTO")
            item_rows.append(
                {
                    "item_nota_fiscal": nf_item,
                    "item_pedido": suggestion,
                    "resultado": ConferenciaItem.Resultado.SUGESTAO_TEXTO,
                    "quantidade_nf": nf_item.quantidade,
                    "saldo_pedido": suggestion.saldo_cache,
                    "quantidade_cabe": Decimal("0"),
                    "excesso": Decimal("0"),
                    "alertas": ["SUGESTAO_TEXTO"],
                    "observacao": "Similaridade textual sem codigo nao conta como match.",
                    "ordem": order,
                }
            )
        else:
            alerts.add("EXTRA_NF")
            item_rows.append(
                {
                    "item_nota_fiscal": nf_item,
                    "item_pedido": None,
                    "resultado": ConferenciaItem.Resultado.EXTRA_NF,
                    "quantidade_nf": nf_item.quantidade,
                    "saldo_pedido": Decimal("0"),
                    "quantidade_cabe": Decimal("0"),
                    "excesso": Decimal("0"),
                    "alertas": ["EXTRA_NF"],
                    "observacao": "Item da NF ausente no pedido.",
                    "ordem": order,
                }
            )

    nf_codes = {item.codigo_normalizado for item in nf_items if item.codigo_normalizado}
    absent_order_items = [
        item
        for item in order_items
        if item.id not in used_order_item_ids and item.codigo_normalizado and item.codigo_normalizado not in nf_codes
    ]
    for offset, order_item in enumerate(absent_order_items, start=len(item_rows) + 1):
        item_rows.append(
            {
                "item_nota_fiscal": None,
                "item_pedido": order_item,
                "resultado": ConferenciaItem.Resultado.SALDO_RESTANTE,
                "quantidade_nf": Decimal("0"),
                "saldo_pedido": order_item.saldo_cache,
                "quantidade_cabe": Decimal("0"),
                "excesso": Decimal("0"),
                "alertas": [],
                "observacao": "Item do pedido permanece em saldo para faturamento futuro.",
                "ordem": offset,
            }
        )

    relevant_nf_count = Decimal(len(nf_items))
    coverage_items = percent((confirmed_count / relevant_nf_count) * PERCENT) if relevant_nf_count else Decimal("0.00")
    if quantity_coverages:
        coverage_quantities = percent((sum(quantity_coverages, Decimal("0")) / Decimal(len(quantity_coverages))) * PERCENT)
    else:
        coverage_quantities = Decimal("0.00")
    compatibility = min(coverage_items, coverage_quantities)
    return CandidateScore(
        pedido=pedido,
        coverage_items=coverage_items,
        coverage_quantities=coverage_quantities,
        compatibility=compatibility,
        level=level_for(compatibility),
        alerts=sorted(alerts),
        item_rows=item_rows,
    )


@transaction.atomic
def recalcular_conferencia_para_nota(nota_fiscal: NotaFiscal) -> Conferencia:
    Conferencia.objects.filter(nota_fiscal=nota_fiscal, vigente=True).update(vigente=False)
    conferencia = Conferencia.objects.create(
        empresa_cliente=nota_fiscal.empresa_cliente,
        nota_fiscal=nota_fiscal,
        mensagem="Loja pendente de revisao." if not nota_fiscal.loja_id else "",
    )

    scores = [score_candidate(nota_fiscal, pedido) for pedido in candidate_orders_for_invoice(nota_fiscal)]
    scores.sort(key=lambda item: (-item.compatibility, item.pedido.data_operacional, item.pedido.criado_em))

    if not scores and nota_fiscal.loja_id:
        conferencia.mensagem = "Nenhuma planilha candidata com saldo foi encontrada."
        conferencia.save(update_fields=["mensagem"])
        return conferencia

    top_compatibility = scores[0].compatibility if scores else None
    top_count = sum(1 for score in scores if score.compatibility == top_compatibility) if scores else 0

    for order, score in enumerate(scores, start=1):
        candidata = ConferenciaCandidata.objects.create(
            conferencia=conferencia,
            pedido=score.pedido,
            cobertura_itens=score.coverage_items,
            cobertura_quantidades=score.coverage_quantities,
            compatibilidade=score.compatibility,
            nivel=score.level,
            ambigua=top_count > 1 and score.compatibility == top_compatibility,
            alertas=score.alerts,
            ordem=order,
        )
        ConferenciaItem.objects.bulk_create(
            [
                ConferenciaItem(
                    candidata=candidata,
                    item_nota_fiscal=row["item_nota_fiscal"],
                    item_pedido=row["item_pedido"],
                    resultado=row["resultado"],
                    quantidade_nf=row["quantidade_nf"],
                    saldo_pedido=row["saldo_pedido"],
                    quantidade_cabe=row["quantidade_cabe"],
                    excesso=row["excesso"],
                    alertas=row["alertas"],
                    observacao=row["observacao"],
                    ordem=row["ordem"],
                )
                for row in score.item_rows
            ]
        )
    if top_count > 1:
        conferencia.mensagem = "Candidatas empatadas; escolha administrativa obrigatoria."
        conferencia.save(update_fields=["mensagem"])
    return conferencia

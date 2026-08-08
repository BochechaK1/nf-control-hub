from pathlib import Path
from uuid import uuid4
import hashlib

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook

from audit.models import EventoAuditoria
from audit.services import registrar_evento
from files.models import Arquivo

from .models import Exportacao


def export_relative_path(filename: str) -> Path:
    now = timezone.localtime()
    return Path("exportacao") / f"{now:%Y}" / f"{now:%m}" / filename


@transaction.atomic
def gerar_copia_preenchida_associacao(*, associacao, usuario) -> Exportacao:
    existing = associacao.exportacoes.filter(tipo=Exportacao.Tipo.COPIA_PREENCHIDA).select_related("arquivo").first()
    if existing:
        return existing

    workbook = Workbook()
    ws = workbook.active
    ws.title = "NF Control Hub"
    ws.append(["Copia preenchida - apoio operacional"])
    ws.append(["NF", associacao.nota_fiscal.numero])
    ws.append(["Serie", associacao.nota_fiscal.serie])
    ws.append(["Fornecedor", associacao.nota_fiscal.fornecedor.nome])
    ws.append(["Pedido", str(associacao.pedido)])
    ws.append(["Aprovada em", timezone.localtime(associacao.aprovada_em).strftime("%Y-%m-%d %H:%M:%S")])
    ws.append([])
    ws.append(["Codigo NF", "Produto NF", "Quantidade NF", "Codigo Pedido", "Produto Pedido", "Quantidade alocada"])
    for allocation in associacao.alocacoes.select_related("item_nota_fiscal", "item_pedido").order_by("id"):
        ws.append(
            [
                allocation.item_nota_fiscal.codigo_original,
                allocation.item_nota_fiscal.descricao_original,
                float(allocation.item_nota_fiscal.quantidade),
                allocation.item_pedido.codigo_original,
                allocation.item_pedido.produto_original,
                float(allocation.quantidade),
            ]
        )

    filename = f"{uuid4().hex}_copia_preenchida_nf_{associacao.nota_fiscal.numero}.xlsx"
    relative_path = export_relative_path(filename)
    absolute_path = settings.NFCH_STORAGE_ROOT / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(absolute_path)
    workbook.close()

    content = absolute_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    arquivo = Arquivo.objects.create(
        empresa_cliente=associacao.empresa_cliente,
        tipo=Arquivo.Tipo.EXPORTACAO,
        nome_original=filename,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        tamanho=len(content),
        hash_sha256=digest,
        caminho_relativo=relative_path.as_posix(),
        usuario_importacao=usuario,
        politica_retencao="COPIA_PREENCHIDA_MVP",
    )
    exportacao = Exportacao.objects.create(
        empresa_cliente=associacao.empresa_cliente,
        associacao=associacao,
        arquivo=arquivo,
        tipo=Exportacao.Tipo.COPIA_PREENCHIDA,
        gerada_por=usuario,
        observacao="Copia preenchida gerada a partir de associacao aprovada.",
    )
    registrar_evento(
        empresa_cliente=associacao.empresa_cliente,
        usuario=usuario,
        origem=EventoAuditoria.Origem.USUARIO,
        entidade=exportacao,
        acao="EXPORTACAO_GERADA",
        depois={
            "associacao_id": associacao.id,
            "arquivo_id": arquivo.id,
            "hash_sha256": arquivo.hash_sha256,
        },
    )
    return exportacao

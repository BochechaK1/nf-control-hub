from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from defusedxml import ElementTree
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from audit.models import EventoAuditoria
from audit.services import registrar_evento
from diagnostics.models import Diagnostico, TarefaProcessamento
from diagnostics.services import registrar_diagnostico
from files.models import Arquivo
from files.services import store_uploaded_file
from orders.services import normalize_code, normalize_text
from organizations.models import Fornecedor, Loja

from .models import ItemNotaFiscal, NotaFiscal


class NFeImportError(Exception):
    def __init__(self, message: str, detail: str = "", diagnostic_type: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.diagnostic_type = diagnostic_type or Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA


@dataclass(frozen=True)
class ParsedInvoiceItem:
    numero_item: int
    codigo_original: str
    codigo_normalizado: str
    descricao_original: str
    descricao_normalizada: str
    ean_original: str
    ncm: str
    cfop: str
    unidade_original: str
    unidade_normalizada: str
    quantidade_original: str
    quantidade: Decimal
    valor_unitario_original: str
    valor_unitario: Decimal | None
    valor_produto_original: str
    valor_produto: Decimal | None
    xped_original: str
    nitemped_original: str


@dataclass(frozen=True)
class ParsedInvoice:
    chave_acesso: str
    modelo: str
    numero: str
    serie: str
    data_emissao: datetime
    natureza_operacao: str
    emitente_cnpj: str
    emitente_nome: str
    destinatario_cnpj: str
    destinatario_nome: str
    valor_total: Decimal
    items: list[ParsedInvoiceItem]


@dataclass(frozen=True)
class InvoiceImportResult:
    arquivo: Arquivo
    nota_fiscal: NotaFiscal | None
    created: bool
    duplicate: bool
    diagnostics_count: int = 0


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(element, name: str):
    if element is None:
        return None
    for item in list(element):
        if local_name(item.tag) == name:
            return item
    return None


def first_descendant(element, name: str):
    if element is None:
        return None
    for item in element.iter():
        if local_name(item.tag) == name:
            return item
    return None


def text(element, name: str, default: str = "") -> str:
    found = child(element, name)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def only_digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def parse_decimal(value: str, default: Decimal | None = None) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return default
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise NFeImportError("Valor numerico invalido no XML.", f"Valor recebido: {value}") from exc


def parse_nfe_datetime(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        parsed_date = parse_date(value)
        if parsed_date is None:
            raise NFeImportError("Data de emissao ausente ou invalida no XML.", f"Valor recebido: {value}")
        parsed = datetime.combine(parsed_date, time.min)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def access_key_from(inf_nfe, prot_nfe) -> str:
    protocol_key = text(first_descendant(prot_nfe, "infProt"), "chNFe")
    if protocol_key:
        return only_digits(protocol_key)
    raw_id = inf_nfe.attrib.get("Id", "")
    if raw_id.startswith("NFe"):
        raw_id = raw_id[3:]
    return only_digits(raw_id)


def parse_nfe_xml(path: Path) -> ParsedInvoice:
    try:
        tree = ElementTree.parse(path)
    except Exception as exc:
        raise NFeImportError("XML ilegivel.", str(exc), Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA) from exc

    root = tree.getroot()
    inf_nfe = first_descendant(root, "infNFe")
    if inf_nfe is None:
        raise NFeImportError(
            "Estrutura de NF-e nao reconhecida.",
            "Elemento infNFe nao encontrado.",
            Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA,
        )

    prot_nfe = first_descendant(root, "protNFe")
    cstat = text(first_descendant(prot_nfe, "infProt"), "cStat")
    if cstat != "100":
        raise NFeImportError(
            "XML da NF-e nao autorizado.",
            f"cStat recebido: {cstat or 'ausente'}",
            Diagnostico.Tipo.DOCUMENTO_NAO_SUPORTADO,
        )

    ide = child(inf_nfe, "ide")
    emit = child(inf_nfe, "emit")
    dest = child(inf_nfe, "dest")
    total = child(child(inf_nfe, "total"), "ICMSTot")
    if ide is None or emit is None or dest is None:
        raise NFeImportError(
            "Cabecalho fiscal incompleto no XML.",
            "Elementos ide, emit ou dest ausentes.",
            Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA,
        )

    model = text(ide, "mod")
    if model != "55":
        raise NFeImportError(
            "Documento fiscal nao suportado no MVP.",
            f"Modelo recebido: {model or 'ausente'}",
            Diagnostico.Tipo.DOCUMENTO_NAO_SUPORTADO,
        )

    key = access_key_from(inf_nfe, prot_nfe)
    if len(key) != 44:
        raise NFeImportError("Chave de acesso invalida no XML.", f"Chave recebida: {key}")

    items: list[ParsedInvoiceItem] = []
    for det in [node for node in inf_nfe if local_name(node.tag) == "det"]:
        product = child(det, "prod")
        if product is None:
            continue
        qcom_original = text(product, "qCom")
        qcom = parse_decimal(qcom_original)
        if qcom is None or qcom <= 0:
            raise NFeImportError(
                "Item fiscal com quantidade invalida.",
                f"nItem={det.attrib.get('nItem', '')}; qCom={qcom_original}",
            )
        code = text(product, "cProd")
        description = text(product, "xProd")
        unit = text(product, "uCom")
        unit_value_original = text(product, "vUnCom")
        product_value_original = text(product, "vProd")
        items.append(
            ParsedInvoiceItem(
                numero_item=int(det.attrib.get("nItem", len(items) + 1)),
                codigo_original=code,
                codigo_normalizado=normalize_code(code),
                descricao_original=description,
                descricao_normalizada=normalize_text(description),
                ean_original=text(product, "cEAN"),
                ncm=text(product, "NCM"),
                cfop=text(product, "CFOP"),
                unidade_original=unit,
                unidade_normalizada=normalize_text(unit),
                quantidade_original=qcom_original,
                quantidade=qcom,
                valor_unitario_original=unit_value_original,
                valor_unitario=parse_decimal(unit_value_original),
                valor_produto_original=product_value_original,
                valor_produto=parse_decimal(product_value_original),
                xped_original=text(product, "xPed"),
                nitemped_original=text(product, "nItemPed"),
            )
        )

    if not items:
        raise NFeImportError("XML da NF-e sem itens fiscais.", "Nenhum det/prod valido foi encontrado.")

    return ParsedInvoice(
        chave_acesso=key,
        modelo=model,
        numero=text(ide, "nNF"),
        serie=text(ide, "serie"),
        data_emissao=parse_nfe_datetime(text(ide, "dhEmi") or text(ide, "dEmi")),
        natureza_operacao=text(ide, "natOp"),
        emitente_cnpj=only_digits(text(emit, "CNPJ")),
        emitente_nome=text(emit, "xNome"),
        destinatario_cnpj=only_digits(text(dest, "CNPJ")),
        destinatario_nome=text(dest, "xNome"),
        valor_total=parse_decimal(text(total, "vNF"), Decimal("0")) or Decimal("0"),
        items=items,
    )


def locate_store(*, empresa_cliente, destinatario_cnpj: str) -> tuple[Loja | None, str]:
    stores = list(
        Loja.objects.filter(
            empresa_cliente=empresa_cliente,
            cnpj_normalizado=destinatario_cnpj,
            ativa=True,
        )
    )
    if len(stores) == 1:
        return stores[0], NotaFiscal.SituacaoFila.AGUARDANDO_MATCH
    if len(stores) > 1:
        return None, NotaFiscal.SituacaoFila.LOJA_AMBIGUA
    return None, NotaFiscal.SituacaoFila.LOJA_DESCONHECIDA


def ensure_supplier_from_invoice(*, empresa_cliente, parsed: ParsedInvoice, usuario) -> Fornecedor:
    if not parsed.emitente_cnpj:
        raise NFeImportError(
            "CNPJ do emitente ausente no XML.",
            "Elemento emit/CNPJ nao encontrado.",
            Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA,
        )

    fornecedor, created = Fornecedor.objects.get_or_create(
        empresa_cliente=empresa_cliente,
        cnpj_normalizado=parsed.emitente_cnpj,
        defaults={"nome": parsed.emitente_nome or parsed.emitente_cnpj, "cnpj": parsed.emitente_cnpj},
    )
    if created:
        registrar_evento(
            empresa_cliente=empresa_cliente,
            usuario=usuario,
            origem=EventoAuditoria.Origem.SISTEMA,
            entidade=fornecedor,
            acao="FORNECEDOR_REGISTRADO_AUTOMATICAMENTE",
            depois={
                "nome": fornecedor.nome,
                "cnpj_normalizado": fornecedor.cnpj_normalizado,
                "origem": "XML_NFE_EMITENTE",
            },
        )
    return fornecedor


def import_nfe_xml(*, empresa_cliente, uploaded_file, usuario) -> InvoiceImportResult:
    stored = store_uploaded_file(
        empresa_cliente=empresa_cliente,
        uploaded_file=uploaded_file,
        usuario=usuario,
        tipo=Arquivo.Tipo.XML_NFE,
    )
    if stored.duplicate:
        nota = NotaFiscal.objects.filter(arquivo_xml=stored.arquivo).first()
        return InvoiceImportResult(arquivo=stored.arquivo, nota_fiscal=nota, created=False, duplicate=True)

    tarefa = TarefaProcessamento.objects.create(
        empresa_cliente=empresa_cliente,
        arquivo=stored.arquivo,
        tipo=TarefaProcessamento.Tipo.IMPORTAR_XML,
        estado=TarefaProcessamento.Estado.PROCESSANDO,
        progresso=10,
    )
    path = settings.NFCH_STORAGE_ROOT / stored.arquivo.caminho_relativo

    try:
        parsed = parse_nfe_xml(path)
        existing = NotaFiscal.objects.filter(empresa_cliente=empresa_cliente, chave_acesso=parsed.chave_acesso).first()
        if existing:
            stored.arquivo.situacao = Arquivo.Situacao.ERRO
            stored.arquivo.save(update_fields=["situacao"])
            tarefa.estado = TarefaProcessamento.Estado.ERRO
            tarefa.progresso = 100
            tarefa.mensagem_usuario = "Chave de acesso ja existe com conteudo divergente."
            tarefa.erro_tecnico = f"NF existente arquivo={existing.arquivo_xml_id}; novo arquivo={stored.arquivo.id}"
            tarefa.save(update_fields=["estado", "progresso", "mensagem_usuario", "erro_tecnico", "atualizada_em"])
            registrar_diagnostico(
                empresa_cliente=empresa_cliente,
                arquivo=stored.arquivo,
                tipo=Diagnostico.Tipo.CHAVE_DIVERGENTE,
                mensagem_usuario="XML com chave ja importada possui conteudo divergente.",
                detalhe_tecnico=tarefa.erro_tecnico,
                criado_por=usuario,
            )
            return InvoiceImportResult(arquivo=stored.arquivo, nota_fiscal=None, created=False, duplicate=False, diagnostics_count=1)

        loja, situacao_fila = locate_store(empresa_cliente=empresa_cliente, destinatario_cnpj=parsed.destinatario_cnpj)

        with transaction.atomic():
            fornecedor = ensure_supplier_from_invoice(
                empresa_cliente=empresa_cliente,
                parsed=parsed,
                usuario=usuario,
            )
            nota = NotaFiscal.objects.create(
                empresa_cliente=empresa_cliente,
                arquivo_xml=stored.arquivo,
                fornecedor=fornecedor,
                loja=loja,
                chave_acesso=parsed.chave_acesso,
                modelo=parsed.modelo,
                numero=parsed.numero,
                serie=parsed.serie,
                data_emissao=parsed.data_emissao,
                natureza_operacao=parsed.natureza_operacao,
                emitente_cnpj=parsed.emitente_cnpj,
                emitente_nome=parsed.emitente_nome,
                destinatario_cnpj=parsed.destinatario_cnpj,
                destinatario_nome=parsed.destinatario_nome,
                valor_total=parsed.valor_total,
                situacao_fila=situacao_fila,
            )
            ItemNotaFiscal.objects.bulk_create(
                [
                    ItemNotaFiscal(
                        nota_fiscal=nota,
                        empresa_cliente=empresa_cliente,
                        numero_item=item.numero_item,
                        codigo_original=item.codigo_original,
                        codigo_normalizado=item.codigo_normalizado,
                        descricao_original=item.descricao_original,
                        descricao_normalizada=item.descricao_normalizada,
                        ean_original=item.ean_original,
                        ncm=item.ncm,
                        cfop=item.cfop,
                        unidade_original=item.unidade_original,
                        unidade_normalizada=item.unidade_normalizada,
                        quantidade_original=item.quantidade_original,
                        quantidade=item.quantidade,
                        valor_unitario_original=item.valor_unitario_original,
                        valor_unitario=item.valor_unitario,
                        valor_produto_original=item.valor_produto_original,
                        valor_produto=item.valor_produto,
                        xped_original=item.xped_original,
                        nitemped_original=item.nitemped_original,
                    )
                    for item in parsed.items
                ]
            )
            tarefa.estado = TarefaProcessamento.Estado.CONCLUIDO
            tarefa.progresso = 100
            tarefa.mensagem_usuario = f"NF-e importada com {len(parsed.items)} item(ns)."
            tarefa.save(update_fields=["estado", "progresso", "mensagem_usuario", "atualizada_em"])
            registrar_evento(
                empresa_cliente=empresa_cliente,
                usuario=usuario,
                origem=EventoAuditoria.Origem.USUARIO,
                entidade=nota,
                acao="NFE_IMPORTADA",
                depois={
                    "arquivo_id": stored.arquivo.id,
                    "chave_acesso": nota.chave_acesso,
                    "numero": nota.numero,
                    "serie": nota.serie,
                    "itens": len(parsed.items),
                    "situacao_fila": nota.situacao_fila,
                },
            )
        return InvoiceImportResult(arquivo=stored.arquivo, nota_fiscal=nota, created=True, duplicate=False)
    except NFeImportError as exc:
        stored.arquivo.situacao = Arquivo.Situacao.ERRO
        stored.arquivo.save(update_fields=["situacao"])
        tarefa.estado = TarefaProcessamento.Estado.ERRO
        tarefa.progresso = 100
        tarefa.mensagem_usuario = exc.message
        tarefa.erro_tecnico = exc.detail
        tarefa.save(update_fields=["estado", "progresso", "mensagem_usuario", "erro_tecnico", "atualizada_em"])
        registrar_diagnostico(
            empresa_cliente=empresa_cliente,
            arquivo=stored.arquivo,
            tipo=exc.diagnostic_type,
            mensagem_usuario=exc.message,
            detalhe_tecnico=exc.detail,
            criado_por=usuario,
        )
        return InvoiceImportResult(arquivo=stored.arquivo, nota_fiscal=None, created=False, duplicate=False, diagnostics_count=1)

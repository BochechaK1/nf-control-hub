from io import BytesIO
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook

from accounts.models import Usuario
from diagnostics.models import Diagnostico, TarefaProcessamento
from files.models import Arquivo
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import ItemPedido, Pedido
from .services import import_order_spreadsheet, normalize_code


def workbook_upload(rows, filename="MATRIZ (2).xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Pedido"
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return SimpleUploadedFile(
        filename,
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class CoralOrderImportTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(NFCH_STORAGE_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.empresa = EmpresaCliente.objects.create(nome="Destiny In", codigo="destiny")
        self.loja = Loja.objects.create(empresa_cliente=self.empresa, codigo="matriz", nome="Matriz")
        self.fornecedor = Fornecedor.objects.create(
            empresa_cliente=self.empresa,
            nome="Coral",
            cnpj="22.222.222/0001-22",
        )
        self.user = Usuario.objects.create_superuser(username="kauan", password="secret")

    def test_import_preserves_originals_and_creates_initial_balance(self):
        upload = workbook_upload(
            [
                ["Pedido W000062885", None, None, None, None, None],
                ["CODIGO DO ITEM", "PRODUTO", "QUANTIDADE", "UNIDADE", "TAMANHO", "PRECO"],
                ["000123", "Tinta branco", "10", "BD", "18 L", "99,90"],
                ["000456", "Massa corrida", 0, "CX", "25 kg", "50,00"],
                ["000789", "Selador", None, "UN", "3,6 L", "20,00"],
                ["001111", "Esmalte", "2,5", "UN", "900 ml", "30,00"],
            ]
        )

        result = import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=upload,
            usuario=self.user,
        )

        self.assertTrue(result.created)
        self.assertEqual(Pedido.objects.count(), 1)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.numero_pedido, "W000062885")
        self.assertEqual(pedido.estado, Pedido.Estado.ABERTA)
        self.assertEqual(pedido.itens.count(), 2)

        item = ItemPedido.objects.get(codigo_original="000123")
        self.assertEqual(item.codigo_normalizado, "123")
        self.assertEqual(item.produto_original, "Tinta branco")
        self.assertEqual(item.quantidade_original, "10")
        self.assertEqual(item.quantidade_pedida, item.saldo_cache)
        self.assertEqual(item.faturado_cache, 0)
        self.assertEqual(item.recebido_cache, 0)
        self.assertEqual(str(item.preco_estimado), "99.9000")

    def test_identical_reimport_is_duplicate(self):
        rows = [
            ["CODIGO DO ITEM", "PRODUTO", "QUANTIDADE"],
            ["000123", "Tinta branco", "10"],
        ]
        payload_file = workbook_upload(rows)
        payload = payload_file.read()
        first = SimpleUploadedFile(
            payload_file.name,
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        second = SimpleUploadedFile(
            payload_file.name,
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=first,
            usuario=self.user,
        )
        result = import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=second,
            usuario=self.user,
        )

        self.assertTrue(result.duplicate)
        self.assertEqual(Arquivo.objects.count(), 1)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_negative_quantity_becomes_diagnostic_without_order(self):
        upload = workbook_upload(
            [
                ["CODIGO DO ITEM", "PRODUTO", "QUANTIDADE"],
                ["000123", "Tinta branco", "-1"],
            ]
        )

        result = import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=upload,
            usuario=self.user,
        )

        self.assertIsNone(result.pedido)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Diagnostico.objects.count(), 1)
        self.assertEqual(Diagnostico.objects.get().tipo, Diagnostico.Tipo.LINHA_INVALIDA)

    def test_imports_iquine_layout_with_product_column_as_code(self):
        upload = workbook_upload(
            [
                [None, None, "Tabela - Julho 2026", None, None, None, None, None, None, None, None, None],
                [None, None, None, "COLUNA NOVA", None, None, None, None, None, None, None, None],
                [
                    None,
                    "Produto",
                    "Descrição",
                    "PREÇO S/IMP",
                    "PREÇO S/IMP",
                    "PREÇO S/IMP 2026",
                    "IPI",
                    "PREÇO C/IPI",
                    "ST",
                    "PREÇO C/ST.",
                    "QUANTID.",
                    "TOTAL",
                ],
                ["AGUARRAS", "117100011", "AGUARRAS IQUINE 5,0 L", "54,94", "", "", "", "", "", "", "", "0"],
                ["", "613305730R", "CORANTE LIQUIDO PRETO 50ML", "2,02", "", "", "", "", "", "", "36", "89,27"],
                ["", "383332901", "DECORATTO CIM QUEIMADO CZ CLARO 5KG", "49,54", "", "", "", "", "", "", "4", "235,29"],
                ["", "", "", "", "", "", "", "", "", "", "TOTAL", "324,56"],
            ],
            filename="IQUINE PARATY.xlsx",
        )

        self.fornecedor.nome = "Iquine"
        self.fornecedor.save(update_fields=["nome"])
        result = import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=upload,
            usuario=self.user,
        )

        self.assertTrue(result.created)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(ItemPedido.objects.count(), 2)
        first = ItemPedido.objects.get(codigo_original="613305730R")
        self.assertEqual(first.codigo_normalizado, "613305730R")
        self.assertEqual(first.produto_original, "CORANTE LIQUIDO PRETO 50ML")
        self.assertEqual(first.quantidade_original, "36")
        self.assertEqual(first.quantidade_pedida, first.saldo_cache)
        self.assertEqual(str(first.preco_estimado), "2.0200")

    def test_reprocesses_duplicate_file_that_only_had_diagnostic(self):
        upload = workbook_upload(
            [
                ["CODIGO DO ITEM", "PRODUTO", "QUANTIDADE"],
                ["000123", "Tinta branco", "10"],
            ],
            filename="IQUINE MATRIZ.xlsx",
        )
        payload = upload.read()
        digest = hashlib.sha256(payload).hexdigest()
        relative_path = Path("planilha_pedido/2026/08/iquine.xlsx")
        absolute_path = settings.NFCH_STORAGE_ROOT / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(payload)
        arquivo = Arquivo.objects.create(
            empresa_cliente=self.empresa,
            tipo=Arquivo.Tipo.PLANILHA_PEDIDO,
            nome_original=upload.name,
            tamanho=len(payload),
            hash_sha256=digest,
            caminho_relativo=relative_path.as_posix(),
            usuario_importacao=self.user,
            situacao=Arquivo.Situacao.ERRO,
        )
        TarefaProcessamento.objects.create(
            empresa_cliente=self.empresa,
            arquivo=arquivo,
            tipo=TarefaProcessamento.Tipo.IMPORTAR_PLANILHA,
            estado=TarefaProcessamento.Estado.ERRO,
            mensagem_usuario="Estrutura da planilha nao reconhecida.",
        )
        Diagnostico.objects.create(
            empresa_cliente=self.empresa,
            arquivo=arquivo,
            tipo=Diagnostico.Tipo.ESTRUTURA_NAO_RECONHECIDA,
            mensagem_usuario="Estrutura da planilha nao reconhecida.",
            criado_por=self.user,
        )

        result = import_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=SimpleUploadedFile(
                upload.name,
                payload,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            usuario=self.user,
        )

        self.assertTrue(result.created)
        self.assertFalse(result.duplicate)
        self.assertEqual(Pedido.objects.count(), 1)
        arquivo.refresh_from_db()
        self.assertEqual(arquivo.situacao, Arquivo.Situacao.ARMAZENADO)
        self.assertEqual(Diagnostico.objects.get().status, Diagnostico.Status.RESOLVIDO)

    def test_supplier_code_normalizes_leading_zeroes(self):
        self.assertEqual(normalize_code("000123"), "123")
        self.assertEqual(normalize_code(" ab-001 "), "AB001")

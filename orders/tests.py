from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook

from accounts.models import Usuario
from diagnostics.models import Diagnostico
from files.models import Arquivo
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import ItemPedido, Pedido
from .services import import_coral_order_spreadsheet, normalize_code


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

        result = import_coral_order_spreadsheet(
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
        first = workbook_upload(rows)
        second = workbook_upload(rows)

        import_coral_order_spreadsheet(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            uploaded_file=first,
            usuario=self.user,
        )
        result = import_coral_order_spreadsheet(
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

        result = import_coral_order_spreadsheet(
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

    def test_supplier_code_normalizes_leading_zeroes(self):
        self.assertEqual(normalize_code("000123"), "123")
        self.assertEqual(normalize_code(" ab-001 "), "AB001")

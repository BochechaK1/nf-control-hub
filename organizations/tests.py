from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from .models import EmpresaCliente, Fornecedor, Loja


class OrganizationModelTests(TestCase):
    def test_cnpj_is_normalized_without_changing_original(self):
        empresa = EmpresaCliente.objects.create(nome="Destiny In", codigo="destiny", cnpj="12.345.678/0001-90")

        self.assertEqual(empresa.cnpj, "12.345.678/0001-90")
        self.assertEqual(empresa.cnpj_normalizado, "12345678000190")

    def test_loja_and_fornecedor_are_scoped_by_empresa(self):
        empresa = EmpresaCliente.objects.create(nome="Cliente", codigo="cliente")

        loja = Loja.objects.create(
            empresa_cliente=empresa,
            codigo="matriz",
            nome="Matriz",
            cnpj="11.111.111/0001-11",
        )
        fornecedor = Fornecedor.objects.create(
            empresa_cliente=empresa,
            nome="Coral",
            cnpj="22.222.222/0001-22",
        )

        self.assertEqual(loja.empresa_cliente, empresa)
        self.assertEqual(fornecedor.empresa_cliente, empresa)
        self.assertEqual(loja.cnpj_normalizado, "11111111000111")
        self.assertEqual(fornecedor.cnpj_normalizado, "22222222000122")

    def test_import_lojas_cnpjs_command_creates_and_updates_stores(self):
        empresa = EmpresaCliente.objects.create(nome="Cliente", codigo="cliente")

        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "lojas.csv"
            csv_path.write_text(
                "codigo,nome,cnpj\n"
                "matriz,Matriz,11.111.111/0001-11\n",
                encoding="utf-8",
            )
            output = StringIO()

            call_command(
                "import_lojas_cnpjs",
                str(csv_path),
                "--empresa-codigo=cliente",
                stdout=output,
            )

            loja = Loja.objects.get(empresa_cliente=empresa, codigo="matriz")
            self.assertEqual(loja.nome, "Matriz")
            self.assertEqual(loja.cnpj_normalizado, "11111111000111")

            csv_path.write_text(
                "codigo,nome,cnpj\n"
                "matriz-loja,Matriz Loja,11.111.111/0001-11\n",
                encoding="utf-8",
            )
            call_command(
                "import_lojas_cnpjs",
                str(csv_path),
                "--empresa-codigo=cliente",
                stdout=StringIO(),
            )

        loja.refresh_from_db()
        self.assertEqual(loja.codigo, "matriz-loja")
        self.assertEqual(loja.nome, "Matriz Loja")
        self.assertEqual(Loja.objects.count(), 1)

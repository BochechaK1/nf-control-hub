from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario, UsuarioLoja
from approvals.services import aprovar_candidata
from files.models import Arquivo
from invoices.models import ItemNotaFiscal, NotaFiscal
from matching.services import recalcular_conferencia_para_nota
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import Exportacao


class ExportAndDownloadTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(NFCH_STORAGE_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.empresa = EmpresaCliente.objects.create(nome="Destiny In", codigo="destiny")
        self.loja = Loja.objects.create(
            empresa_cliente=self.empresa,
            codigo="matriz",
            nome="Matriz",
            cnpj="11.111.111/0001-11",
        )
        self.outra_loja = Loja.objects.create(
            empresa_cliente=self.empresa,
            codigo="filial",
            nome="Filial",
            cnpj="22.111.111/0001-11",
        )
        self.fornecedor = Fornecedor.objects.create(
            empresa_cliente=self.empresa,
            nome="Coral",
            cnpj="22.222.222/0001-22",
        )
        self.admin = Usuario.objects.create_superuser(username="kauan", password="secret")
        self.viewer = Usuario.objects.create_user(
            username="viewer",
            password="secret",
            role=Usuario.Role.VISUALIZADOR,
            empresa_cliente=self.empresa,
        )
        UsuarioLoja.objects.create(usuario=self.viewer, loja=self.loja)
        self.file_counter = 0

    def arquivo(self, tipo):
        self.file_counter += 1
        return Arquivo.objects.create(
            empresa_cliente=self.empresa,
            tipo=tipo,
            nome_original=f"arquivo-{self.file_counter}.xlsx",
            tamanho=10,
            hash_sha256=f"{self.file_counter:064d}",
            caminho_relativo=f"arquivo-{self.file_counter}.xlsx",
        )

    def make_approved_association(self):
        pedido = Pedido.objects.create(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            arquivo=self.arquivo(Arquivo.Tipo.PLANILHA_PEDIDO),
            numero_pedido="P-001",
            data_operacional=timezone.localdate(),
        )
        ItemPedido.objects.create(
            pedido=pedido,
            empresa_cliente=self.empresa,
            fornecedor=self.fornecedor,
            aba="Pedido",
            linha=1,
            codigo_original="000123",
            codigo_normalizado="123",
            produto_original="Tinta branco",
            produto_normalizado="TINTA BRANCO",
            quantidade_original="10",
            quantidade_pedida=Decimal("10"),
            unidade_original="UN",
            unidade_normalizada="UN",
            saldo_cache=Decimal("10"),
        )
        nota = NotaFiscal.objects.create(
            empresa_cliente=self.empresa,
            arquivo_xml=self.arquivo(Arquivo.Tipo.XML_NFE),
            fornecedor=self.fornecedor,
            loja=self.loja,
            chave_acesso="1".zfill(44),
            modelo="55",
            numero="100",
            serie="1",
            data_emissao=timezone.now(),
            emitente_cnpj=self.fornecedor.cnpj_normalizado,
            emitente_nome=self.fornecedor.nome,
            destinatario_cnpj=self.loja.cnpj_normalizado,
            destinatario_nome=self.loja.nome,
        )
        ItemNotaFiscal.objects.create(
            nota_fiscal=nota,
            empresa_cliente=self.empresa,
            numero_item=1,
            codigo_original="000123",
            codigo_normalizado="123",
            descricao_original="Tinta branco",
            descricao_normalizada="TINTA BRANCO",
            unidade_original="UN",
            unidade_normalizada="UN",
            quantidade_original="10",
            quantidade=Decimal("10"),
        )
        candidate = recalcular_conferencia_para_nota(nota).candidatas.first()
        return aprovar_candidata(candidata=candidate, usuario=self.admin)

    def test_approval_generates_filled_copy_export(self):
        association = self.make_approved_association()

        export = Exportacao.objects.get(associacao=association)
        path = Path(self.tmp.name) / export.arquivo.caminho_relativo
        self.assertEqual(export.tipo, Exportacao.Tipo.COPIA_PREENCHIDA)
        self.assertTrue(path.exists())
        self.assertGreater(export.arquivo.tamanho, 0)

    def test_authorized_viewer_can_download_store_file(self):
        association = self.make_approved_association()
        export = Exportacao.objects.get(associacao=association)
        client = Client()
        client.force_login(self.viewer)

        response = client.get(reverse("ui:download_arquivo", args=[export.arquivo.id]))

        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        finally:
            response.close()

    def test_viewer_cannot_download_unlinked_store_file(self):
        association = self.make_approved_association()
        association.pedido.loja = self.outra_loja
        association.pedido.save(update_fields=["loja"])
        export = Exportacao.objects.get(associacao=association)
        client = Client()
        client.force_login(self.viewer)

        response = client.get(reverse("ui:download_arquivo", args=[export.arquivo.id]))

        self.assertEqual(response.status_code, 404)

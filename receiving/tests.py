from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Usuario
from approvals.services import aprovar_candidata
from audit.models import EventoAuditoria
from files.models import Arquivo
from invoices.models import ItemNotaFiscal, NotaFiscal
from matching.services import recalcular_conferencia_para_nota
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import OcorrenciaRecebimento, Recebimento
from .services import alerta_30_dias, anular_recebimento, confirmar_recebimento, dias_aguardando_recebimento


class ReceivingServiceTests(TestCase):
    def setUp(self):
        self.empresa = EmpresaCliente.objects.create(nome="Destiny In", codigo="destiny")
        self.loja = Loja.objects.create(
            empresa_cliente=self.empresa,
            codigo="matriz",
            nome="Matriz",
            cnpj="11.111.111/0001-11",
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
        self.file_counter = 0

    def arquivo(self, tipo):
        self.file_counter += 1
        return Arquivo.objects.create(
            empresa_cliente=self.empresa,
            tipo=tipo,
            nome_original=f"arquivo-{self.file_counter}",
            tamanho=10,
            hash_sha256=f"{self.file_counter:064d}",
            caminho_relativo=f"arquivo-{self.file_counter}",
        )

    def make_approved_invoice(self, *, quantity="10", days_old=0):
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
            quantidade_original=quantity,
            quantidade_pedida=Decimal(quantity),
            unidade_original="UN",
            unidade_normalizada="UN",
            saldo_cache=Decimal(quantity),
        )
        nota = NotaFiscal.objects.create(
            empresa_cliente=self.empresa,
            arquivo_xml=self.arquivo(Arquivo.Tipo.XML_NFE),
            fornecedor=self.fornecedor,
            loja=self.loja,
            chave_acesso=f"{self.file_counter:044d}",
            modelo="55",
            numero=str(100 + self.file_counter),
            serie="1",
            data_emissao=timezone.now() - timedelta(days=days_old),
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
            quantidade_original=quantity,
            quantidade=Decimal(quantity),
        )
        associacao = aprovar_candidata(
            candidata=recalcular_conferencia_para_nota(nota).candidatas.first(),
            usuario=self.admin,
        )
        return pedido, nota, associacao

    def test_ct015_confirm_whole_invoice_without_divergence_moves_billed_to_received(self):
        pedido, nota, associacao = self.make_approved_invoice(quantity="10")

        recebimento = confirmar_recebimento(
            nota_fiscal=nota,
            usuario=self.admin,
            data_recebimento=timezone.localdate(),
        )

        item = pedido.itens.get()
        nota.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(recebimento.resultado, Recebimento.Resultado.SEM_DIVERGENCIA)
        self.assertEqual(item.faturado_cache, Decimal("0.000"))
        self.assertEqual(item.recebido_cache, Decimal("10.000"))
        self.assertEqual(nota.status_recebimento, NotaFiscal.StatusRecebimento.RECEBIDA_SEM_DIVERGENCIA)
        self.assertEqual(pedido.estado, Pedido.Estado.CONCLUIDA)
        self.assertTrue(EventoAuditoria.objects.filter(acao="RECEBIMENTO_CONFIRMADO").exists())

    def test_ct016_divergence_requires_occurrence_and_keeps_highlight(self):
        _, nota, _ = self.make_approved_invoice(quantity="5")

        with self.assertRaises(ValidationError):
            confirmar_recebimento(
                nota_fiscal=nota,
                usuario=self.admin,
                data_recebimento=timezone.localdate(),
                com_divergencia=True,
            )

        recebimento = confirmar_recebimento(
            nota_fiscal=nota,
            usuario=self.admin,
            data_recebimento=timezone.localdate(),
            com_divergencia=True,
            ocorrencia_tipo=OcorrenciaRecebimento.Tipo.FALTA,
            ocorrencia_descricao="Faltou uma caixa na entrega.",
        )

        nota.refresh_from_db()
        self.assertEqual(nota.status_recebimento, NotaFiscal.StatusRecebimento.RECEBIDA_COM_DIVERGENCIA)
        self.assertEqual(recebimento.ocorrencias.count(), 1)

    def test_ct017_invoice_waiting_30_days_generates_informative_alert(self):
        _, nota, _ = self.make_approved_invoice(quantity="1", days_old=31)

        self.assertEqual(dias_aguardando_recebimento(nota), 31)
        self.assertTrue(alerta_30_dias(nota))

    def test_visualizer_cannot_confirm_receiving(self):
        _, nota, _ = self.make_approved_invoice(quantity="1")

        with self.assertRaises(PermissionDenied):
            confirmar_recebimento(
                nota_fiscal=nota,
                usuario=self.viewer,
                data_recebimento=timezone.localdate(),
            )

    def test_annul_receiving_preserves_history_and_moves_back_to_billed(self):
        pedido, nota, _ = self.make_approved_invoice(quantity="3")
        recebimento = confirmar_recebimento(
            nota_fiscal=nota,
            usuario=self.admin,
            data_recebimento=timezone.localdate(),
        )

        anular_recebimento(
            recebimento=recebimento,
            usuario=self.admin,
            justificativa="Recebimento registrado na NF errada.",
        )

        item = pedido.itens.get()
        recebimento.refresh_from_db()
        nota.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(recebimento.status, Recebimento.Status.ANULADO)
        self.assertEqual(item.faturado_cache, Decimal("3.000"))
        self.assertEqual(item.recebido_cache, Decimal("0.000"))
        self.assertEqual(nota.status_recebimento, NotaFiscal.StatusRecebimento.AGUARDANDO_RECEBIMENTO)
        self.assertEqual(pedido.estado, Pedido.Estado.FATURADA)

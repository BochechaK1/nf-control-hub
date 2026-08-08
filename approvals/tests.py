from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Usuario
from files.models import Arquivo
from invoices.models import ItemNotaFiscal, NotaFiscal
from matching.services import recalcular_conferencia_para_nota
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import Alocacao, Associacao
from .services import anular_associacao, aprovar_candidata, reprovar_nota


class ApprovalServiceTests(TestCase):
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

    def pedido(self, items, numero="P-001"):
        pedido = Pedido.objects.create(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            arquivo=self.arquivo(Arquivo.Tipo.PLANILHA_PEDIDO),
            numero_pedido=numero,
            data_operacional=timezone.localdate(),
        )
        for line, item in enumerate(items, start=1):
            quantity = Decimal(str(item["quantity"]))
            ItemPedido.objects.create(
                pedido=pedido,
                empresa_cliente=self.empresa,
                fornecedor=self.fornecedor,
                aba="Pedido",
                linha=line,
                codigo_original=item["code"],
                codigo_normalizado=item["code"].lstrip("0") or item["code"],
                produto_original=item.get("product", f"Produto {item['code']}"),
                produto_normalizado=item.get("product", f"PRODUTO {item['code']}").upper(),
                quantidade_original=str(item["quantity"]),
                quantidade_pedida=quantity,
                unidade_original="UN",
                unidade_normalizada="UN",
                saldo_cache=quantity,
            )
        return pedido

    def nota(self, items, number="100"):
        nota = NotaFiscal.objects.create(
            empresa_cliente=self.empresa,
            arquivo_xml=self.arquivo(Arquivo.Tipo.XML_NFE),
            fornecedor=self.fornecedor,
            loja=self.loja,
            chave_acesso=f"{int(number):044d}",
            modelo="55",
            numero=number,
            serie="1",
            data_emissao=timezone.now(),
            emitente_cnpj=self.fornecedor.cnpj_normalizado,
            emitente_nome=self.fornecedor.nome,
            destinatario_cnpj=self.loja.cnpj_normalizado,
            destinatario_nome=self.loja.nome,
        )
        for index, item in enumerate(items, start=1):
            quantity = Decimal(str(item["quantity"]))
            ItemNotaFiscal.objects.create(
                nota_fiscal=nota,
                empresa_cliente=self.empresa,
                numero_item=index,
                codigo_original=item["code"],
                codigo_normalizado=item["code"].lstrip("0") or item["code"],
                descricao_original=item.get("product", f"Produto {item['code']}"),
                descricao_normalizada=item.get("product", f"PRODUTO {item['code']}").upper(),
                unidade_original="UN",
                unidade_normalizada="UN",
                quantidade_original=str(item["quantity"]),
                quantidade=quantity,
            )
        return nota

    def candidate_for(self, nota):
        return recalcular_conferencia_para_nota(nota).candidatas.first()

    def test_ct002_approve_partial_order_by_items_updates_state_and_keeps_remaining_balance(self):
        pedido = self.pedido([{"code": "X", "quantity": "10"}, {"code": "Y", "quantity": "3"}])
        nota = self.nota([{"code": "X", "quantity": "10"}])
        candidate = self.candidate_for(nota)

        associacao = aprovar_candidata(candidata=candidate, usuario=self.admin, justificativa="Pedido parcial por itens.")

        self.assertEqual(associacao.status, Associacao.Status.VIGENTE)
        self.assertEqual(Alocacao.objects.count(), 1)
        x = ItemPedido.objects.get(pedido=pedido, codigo_original="X")
        y = ItemPedido.objects.get(pedido=pedido, codigo_original="Y")
        pedido.refresh_from_db()
        nota.refresh_from_db()
        self.assertEqual(x.saldo_cache, Decimal("0.000"))
        self.assertEqual(x.faturado_cache, Decimal("10.000"))
        self.assertEqual(y.saldo_cache, Decimal("3.000"))
        self.assertEqual(pedido.estado, Pedido.Estado.PARCIALMENTE_FATURADA)
        self.assertEqual(nota.status_conferencia, NotaFiscal.StatusConferencia.APROVADA)

    def test_ct003_approve_partial_line_updates_balance(self):
        pedido = self.pedido([{"code": "X", "quantity": "10"}])
        nota = self.nota([{"code": "X", "quantity": "6"}])

        aprovar_candidata(candidata=self.candidate_for(nota), usuario=self.admin, justificativa="Linha parcial.")

        item = ItemPedido.objects.get(pedido=pedido, codigo_original="X")
        self.assertEqual(item.saldo_cache, Decimal("4.000"))
        self.assertEqual(item.faturado_cache, Decimal("6.000"))

    def test_ct004_excess_allocates_at_most_balance(self):
        pedido = self.pedido([{"code": "X", "quantity": "10"}])
        nota = self.nota([{"code": "X", "quantity": "12"}])

        assoc = aprovar_candidata(candidata=self.candidate_for(nota), usuario=self.admin, justificativa="Aprovar com excesso registrado.")

        item = ItemPedido.objects.get(pedido=pedido, codigo_original="X")
        allocation = assoc.alocacoes.get()
        self.assertEqual(allocation.quantidade, Decimal("10.0000"))
        self.assertEqual(item.saldo_cache, Decimal("0.000"))
        self.assertEqual(item.faturado_cache, Decimal("10.000"))

    def test_ct008_stale_second_approval_cannot_consume_same_balance(self):
        self.pedido([{"code": "X", "quantity": "10"}])
        nota_a = self.nota([{"code": "X", "quantity": "10"}], number="101")
        nota_b = self.nota([{"code": "X", "quantity": "10"}], number="102")
        candidate_a = self.candidate_for(nota_a)
        candidate_b = self.candidate_for(nota_b)

        aprovar_candidata(candidata=candidate_a, usuario=self.admin)
        with self.assertRaises(ValidationError):
            aprovar_candidata(candidata=candidate_b, usuario=self.admin)

        item = ItemPedido.objects.get(codigo_original="X")
        self.assertEqual(item.saldo_cache, Decimal("0.000"))
        self.assertEqual(item.faturado_cache, Decimal("10.000"))
        self.assertEqual(Associacao.objects.filter(status=Associacao.Status.VIGENTE).count(), 1)

    def test_ct009_annul_restores_balance_and_preserves_history(self):
        pedido = self.pedido([{"code": "X", "quantity": "10"}])
        nota = self.nota([{"code": "X", "quantity": "6"}])
        assoc = aprovar_candidata(candidata=self.candidate_for(nota), usuario=self.admin, justificativa="Linha parcial.")

        anular_associacao(associacao=assoc, usuario=self.admin, justificativa="Erro de associacao.")

        assoc.refresh_from_db()
        item = ItemPedido.objects.get(pedido=pedido, codigo_original="X")
        nota.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(assoc.status, Associacao.Status.ANULADA)
        self.assertEqual(assoc.alocacoes.get().status, Alocacao.Status.ANULADA)
        self.assertEqual(item.saldo_cache, Decimal("10.000"))
        self.assertEqual(item.faturado_cache, Decimal("0.000"))
        self.assertEqual(nota.status_conferencia, NotaFiscal.StatusConferencia.ANULADA)
        self.assertEqual(pedido.estado, Pedido.Estado.ABERTA)

    def test_visualizer_cannot_approve_or_reject(self):
        self.pedido([{"code": "X", "quantity": "1"}])
        nota = self.nota([{"code": "X", "quantity": "1"}])
        candidate = self.candidate_for(nota)

        with self.assertRaises(PermissionDenied):
            aprovar_candidata(candidata=candidate, usuario=self.viewer)
        with self.assertRaises(PermissionDenied):
            reprovar_nota(nota_fiscal=nota, usuario=self.viewer, justificativa="Nao pode.")

    def test_reject_removes_invoice_from_pending_state_without_deleting_it(self):
        nota = self.nota([{"code": "X", "quantity": "1"}])

        reprovar_nota(nota_fiscal=nota, usuario=self.admin, justificativa="Pedido incorreto.")

        nota.refresh_from_db()
        self.assertEqual(nota.status_conferencia, NotaFiscal.StatusConferencia.REJEITADA)
        self.assertTrue(NotaFiscal.objects.filter(pk=nota.pk).exists())

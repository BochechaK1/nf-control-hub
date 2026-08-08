from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from files.models import Arquivo
from invoices.models import ItemNotaFiscal, NotaFiscal
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import ConferenciaCandidata, ConferenciaItem
from .services import recalcular_conferencia_para_nota


class MatchingEngineTests(TestCase):
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

    def pedido(self, items, numero="P-001", days=0):
        pedido = Pedido.objects.create(
            empresa_cliente=self.empresa,
            loja=self.loja,
            fornecedor=self.fornecedor,
            arquivo=self.arquivo(Arquivo.Tipo.PLANILHA_PEDIDO),
            numero_pedido=numero,
            data_operacional=timezone.localdate() + timedelta(days=days),
        )
        for line, item in enumerate(items, start=1):
            quantity = Decimal(str(item["quantity"]))
            ItemPedido.objects.create(
                pedido=pedido,
                empresa_cliente=self.empresa,
                fornecedor=self.fornecedor,
                aba="Pedido",
                linha=line,
                codigo_original=item.get("code", ""),
                codigo_normalizado=item.get("normalized_code", item.get("code", "").lstrip("0")),
                produto_original=item.get("product", "Produto"),
                produto_normalizado=item.get("normalized_product", item.get("product", "PRODUTO").upper()),
                quantidade_original=str(item["quantity"]),
                quantidade_pedida=quantity,
                unidade_original=item.get("unit", "UN"),
                unidade_normalizada=item.get("unit", "UN"),
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
                codigo_original=item.get("code", ""),
                codigo_normalizado=item.get("normalized_code", item.get("code", "").lstrip("0")),
                descricao_original=item.get("product", "Produto"),
                descricao_normalizada=item.get("normalized_product", item.get("product", "PRODUTO").upper()),
                unidade_original=item.get("unit", "UN"),
                unidade_normalizada=item.get("unit", "UN"),
                quantidade_original=str(item["quantity"]),
                quantidade=quantity,
            )
        return nota

    def first_candidate(self, nota):
        conferencia = recalcular_conferencia_para_nota(nota)
        return conferencia.candidatas.first()

    def test_ct002_partial_order_by_items_can_have_full_invoice_coverage(self):
        self.pedido(
            [
                {"code": "X", "product": "Produto X", "quantity": "10"},
                {"code": "Y", "product": "Produto Y", "quantity": "3"},
            ]
        )
        nota = self.nota([{"code": "X", "product": "Produto X", "quantity": "10"}])

        candidate = self.first_candidate(nota)

        self.assertEqual(candidate.compatibilidade, Decimal("100.00"))
        self.assertNotIn("AUSENTE_NF", candidate.alertas)
        self.assertEqual(candidate.itens.filter(resultado=ConferenciaItem.Resultado.CONFIRMADO).count(), 1)
        self.assertEqual(candidate.itens.filter(resultado=ConferenciaItem.Resultado.SALDO_RESTANTE).count(), 1)

    def test_ct003_partial_line_warns_but_quantity_coverage_is_full(self):
        self.pedido([{"code": "X", "product": "Produto X", "quantity": "10"}])
        nota = self.nota([{"code": "X", "product": "Produto X", "quantity": "6"}])

        candidate = self.first_candidate(nota)

        self.assertEqual(candidate.compatibilidade, Decimal("100.00"))
        self.assertIn("PARCIALIDADE_LINHA", candidate.alertas)

    def test_ct004_excess_reduces_quantity_coverage_and_records_excess(self):
        self.pedido([{"code": "X", "product": "Produto X", "quantity": "10"}])
        nota = self.nota([{"code": "X", "product": "Produto X", "quantity": "12"}])

        candidate = self.first_candidate(nota)
        item = candidate.itens.get(resultado=ConferenciaItem.Resultado.CONFIRMADO)

        self.assertEqual(candidate.compatibilidade, Decimal("83.33"))
        self.assertEqual(candidate.nivel, ConferenciaCandidata.Nivel.BAIXA)
        self.assertIn("EXCESSO", candidate.alertas)
        self.assertEqual(item.excesso, Decimal("2.0000"))

    def test_ct005_different_description_with_same_code_confirms_match(self):
        self.pedido([{"code": "000123", "product": "Descricao antiga", "quantity": "5"}])
        nota = self.nota([{"code": "000123", "product": "Descricao fiscal nova", "quantity": "5"}])

        candidate = self.first_candidate(nota)

        self.assertEqual(candidate.compatibilidade, Decimal("100.00"))
        self.assertEqual(candidate.itens.get().resultado, ConferenciaItem.Resultado.CONFIRMADO)

    def test_ct006_text_similarity_without_code_is_only_suggestion(self):
        self.pedido([{"code": "", "normalized_code": "", "product": "TINTA ACRILICA BRANCO", "quantity": "5"}])
        nota = self.nota([{"code": "", "normalized_code": "", "product": "TINTA ACRILICA BRANCO", "quantity": "5"}])

        candidate = self.first_candidate(nota)

        self.assertEqual(candidate.compatibilidade, Decimal("0.00"))
        self.assertIn("SUGESTAO_TEXTO", candidate.alertas)
        self.assertEqual(candidate.itens.get().resultado, ConferenciaItem.Resultado.SUGESTAO_TEXTO)

    def test_ct007_tie_marks_candidates_ambiguous_and_oldest_first(self):
        older = self.pedido([{"code": "X", "product": "Produto X", "quantity": "1"}], numero="P-OLD", days=-2)
        newer = self.pedido([{"code": "X", "product": "Produto X", "quantity": "1"}], numero="P-NEW", days=0)
        nota = self.nota([{"code": "X", "product": "Produto X", "quantity": "1"}])

        conferencia = recalcular_conferencia_para_nota(nota)
        candidates = list(conferencia.candidatas.all())

        self.assertEqual([item.pedido for item in candidates], [older, newer])
        self.assertTrue(all(item.ambigua for item in candidates))

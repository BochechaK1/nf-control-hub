from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from invoices.models import ItemNotaFiscal, NotaFiscal
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente


class Conferencia(models.Model):
    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="conferencias")
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.PROTECT, related_name="conferencias")
    vigente = models.BooleanField(default=True)
    mensagem = models.CharField(max_length=255, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "conferencia"
        verbose_name_plural = "conferencias"
        ordering = ["-criada_em", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["nota_fiscal"],
                condition=Q(vigente=True),
                name="uniq_conf_vigente_nf",
            ),
        ]

    def __str__(self) -> str:
        return f"Conferencia {self.nota_fiscal}"


class ConferenciaCandidata(models.Model):
    class Nivel(models.TextChoices):
        ALTA = "ALTA", "Alta"
        MEDIA = "MEDIA", "Media"
        BAIXA = "BAIXA", "Baixa"

    conferencia = models.ForeignKey(Conferencia, on_delete=models.PROTECT, related_name="candidatas")
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="conferencias_candidatas")
    cobertura_itens = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    cobertura_quantidades = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    compatibilidade = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    nivel = models.CharField(max_length=10, choices=Nivel.choices)
    ambigua = models.BooleanField(default=False)
    alertas = models.JSONField(default=list, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "candidata de conferencia"
        verbose_name_plural = "candidatas de conferencia"
        ordering = ["ordem", "-compatibilidade", "pedido__data_operacional", "pedido__criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["conferencia", "pedido"], name="uniq_conf_pedido"),
        ]

    def __str__(self) -> str:
        return f"{self.pedido} {self.compatibilidade}%"


class ConferenciaItem(models.Model):
    class Resultado(models.TextChoices):
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        SUGESTAO_TEXTO = "SUGESTAO_TEXTO", "Sugestao textual"
        EXTRA_NF = "EXTRA_NF", "Extra na NF"
        SALDO_RESTANTE = "SALDO_RESTANTE", "Saldo restante"

    candidata = models.ForeignKey(ConferenciaCandidata, on_delete=models.PROTECT, related_name="itens")
    item_nota_fiscal = models.ForeignKey(
        ItemNotaFiscal,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="conferencias_item",
    )
    item_pedido = models.ForeignKey(
        ItemPedido,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="conferencias_item",
    )
    resultado = models.CharField(max_length=20, choices=Resultado.choices)
    quantidade_nf = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    saldo_pedido = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    quantidade_cabe = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    excesso = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    alertas = models.JSONField(default=list, blank=True)
    observacao = models.CharField(max_length=255, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "item de conferencia"
        verbose_name_plural = "itens de conferencia"
        ordering = ["ordem", "id"]
        indexes = [
            models.Index(fields=["resultado"], name="confitem_resultado_idx"),
        ]

    def __str__(self) -> str:
        return self.resultado

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from invoices.models import ItemNotaFiscal, NotaFiscal
from matching.models import ConferenciaCandidata
from orders.models import ItemPedido, Pedido
from organizations.models import EmpresaCliente


class Associacao(models.Model):
    class Status(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        ANULADA = "ANULADA", "Anulada"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="associacoes")
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.PROTECT, related_name="associacoes")
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="associacoes")
    candidata = models.ForeignKey(ConferenciaCandidata, on_delete=models.PROTECT, related_name="associacoes")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VIGENTE)
    aprovada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="associacoes_aprovadas",
    )
    aprovada_em = models.DateTimeField(auto_now_add=True)
    justificativa = models.TextField(blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="associacoes_anuladas",
    )
    anulada_em = models.DateTimeField(null=True, blank=True)
    justificativa_anulacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "associacao"
        verbose_name_plural = "associacoes"
        ordering = ["-aprovada_em", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["nota_fiscal"],
                condition=Q(status="VIGENTE"),
                name="uniq_assoc_vigente_nf",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nota_fiscal} -> {self.pedido}"


class Alocacao(models.Model):
    class Status(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        ANULADA = "ANULADA", "Anulada"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="alocacoes")
    associacao = models.ForeignKey(Associacao, on_delete=models.PROTECT, related_name="alocacoes")
    item_nota_fiscal = models.ForeignKey(ItemNotaFiscal, on_delete=models.PROTECT, related_name="alocacoes")
    item_pedido = models.ForeignKey(ItemPedido, on_delete=models.PROTECT, related_name="alocacoes")
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VIGENTE)
    criada_em = models.DateTimeField(auto_now_add=True)
    anulada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "alocacao"
        verbose_name_plural = "alocacoes"
        ordering = ["associacao_id", "id"]
        indexes = [
            models.Index(fields=["empresa_cliente", "status"], name="aloc_emp_status_idx"),
            models.Index(fields=["item_pedido", "status"], name="aloc_itemped_status_idx"),
            models.Index(fields=["item_nota_fiscal", "status"], name="aloc_itemnf_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.item_nota_fiscal_id} -> {self.item_pedido_id}: {self.quantidade}"

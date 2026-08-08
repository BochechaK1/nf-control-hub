from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from files.models import Arquivo
from organizations.models import EmpresaCliente, Fornecedor, Loja


class ModeloPlanilha(models.Model):
    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="modelos_planilha")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name="modelos_planilha")
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "modelo de planilha"
        verbose_name_plural = "modelos de planilha"
        constraints = [
            models.UniqueConstraint(fields=["empresa_cliente", "fornecedor", "nome"], name="uniq_modelo_planilha_forn_nome"),
        ]

    def __str__(self) -> str:
        return self.nome


class ModeloPlanilhaVersao(models.Model):
    modelo = models.ForeignKey(ModeloPlanilha, on_delete=models.PROTECT, related_name="versoes")
    versao = models.PositiveIntegerField(default=1)
    configuracao = models.JSONField(default=dict, blank=True)
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "versao de modelo de planilha"
        verbose_name_plural = "versoes de modelo de planilha"
        constraints = [
            models.UniqueConstraint(fields=["modelo", "versao"], name="uniq_modelo_planilha_versao"),
        ]

    def __str__(self) -> str:
        return f"{self.modelo} v{self.versao}"


class Pedido(models.Model):
    class Estado(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        PARCIALMENTE_FATURADA = "PARCIALMENTE_FATURADA", "Parcialmente faturada"
        FATURADA = "FATURADA", "Faturada"
        PARCIALMENTE_RECEBIDA = "PARCIALMENTE_RECEBIDA", "Parcialmente recebida"
        CONCLUIDA = "CONCLUIDA", "Concluida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="pedidos")
    loja = models.ForeignKey(Loja, on_delete=models.PROTECT, related_name="pedidos")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name="pedidos")
    arquivo = models.OneToOneField(Arquivo, on_delete=models.PROTECT, related_name="pedido")
    modelo_versao = models.ForeignKey(
        ModeloPlanilhaVersao,
        on_delete=models.PROTECT,
        related_name="pedidos",
        null=True,
        blank=True,
    )
    numero_pedido = models.CharField(max_length=80, blank=True)
    data_operacional = models.DateField()
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.ABERTA)
    removido = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["empresa_cliente", "loja", "fornecedor", "estado"], name="ped_emp_loja_forn_est_idx"),
        ]

    def __str__(self) -> str:
        return self.numero_pedido or str(self.id)


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="itens")
    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="itens_pedido")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name="itens_pedido")
    aba = models.CharField(max_length=120)
    linha = models.PositiveIntegerField()
    codigo_original = models.CharField(max_length=120, blank=True)
    codigo_normalizado = models.CharField(max_length=120, blank=True, db_index=True)
    produto_original = models.CharField(max_length=255)
    produto_normalizado = models.CharField(max_length=255)
    quantidade_original = models.CharField(max_length=80)
    quantidade_pedida = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    unidade_original = models.CharField(max_length=40, blank=True)
    unidade_normalizada = models.CharField(max_length=40, blank=True)
    tamanho_original = models.CharField(max_length=80, blank=True)
    tamanho_normalizado = models.CharField(max_length=80, blank=True)
    preco_estimado_original = models.CharField(max_length=80, blank=True)
    preco_estimado = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    saldo_cache = models.DecimalField(max_digits=14, decimal_places=3)
    faturado_cache = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    recebido_cache = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "item de pedido"
        verbose_name_plural = "itens de pedido"
        ordering = ["pedido_id", "aba", "linha", "id"]
        constraints = [
            models.UniqueConstraint(fields=["pedido", "aba", "linha"], name="uniq_item_pedido_aba_linha"),
        ]
        indexes = [
            models.Index(fields=["empresa_cliente", "fornecedor", "codigo_normalizado"], name="itped_emp_forn_cod_idx"),
        ]

    def clean(self):
        super().clean()
        total = self.saldo_cache + self.faturado_cache + self.recebido_cache
        if total != self.quantidade_pedida:
            raise ValidationError("Pedido deve ser igual a saldo + faturado + recebido.")

    def save(self, *args, **kwargs):
        if self.saldo_cache is None:
            self.saldo_cache = self.quantidade_pedida
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.codigo_original} - {self.produto_original}"

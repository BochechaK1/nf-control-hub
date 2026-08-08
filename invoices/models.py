from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from files.models import Arquivo
from organizations.models import EmpresaCliente, Fornecedor, Loja


class NotaFiscal(models.Model):
    class StatusFiscal(models.TextChoices):
        FATURADA = "FATURADA", "Faturada"
        CANCELADA = "CANCELADA", "Cancelada"

    class StatusConferencia(models.TextChoices):
        AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO", "Aguardando aprovacao"
        APROVADA = "APROVADA", "Aprovada"
        REJEITADA = "REJEITADA", "Rejeitada"
        ANULADA = "ANULADA", "Anulada"

    class StatusRecebimento(models.TextChoices):
        AGUARDANDO_RECEBIMENTO = "AGUARDANDO_RECEBIMENTO", "Aguardando recebimento"
        RECEBIDA_SEM_DIVERGENCIA = "RECEBIDA_SEM_DIVERGENCIA", "Recebida sem divergencia"
        RECEBIDA_COM_DIVERGENCIA = "RECEBIDA_COM_DIVERGENCIA", "Recebida com divergencia"

    class SituacaoFila(models.TextChoices):
        AGUARDANDO_MATCH = "AGUARDANDO_MATCH", "Aguardando match"
        LOJA_DESCONHECIDA = "LOJA_DESCONHECIDA", "Loja desconhecida"
        LOJA_AMBIGUA = "LOJA_AMBIGUA", "Loja ambigua"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="notas_fiscais")
    arquivo_xml = models.OneToOneField(Arquivo, on_delete=models.PROTECT, related_name="nota_fiscal")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name="notas_fiscais")
    loja = models.ForeignKey(Loja, on_delete=models.PROTECT, null=True, blank=True, related_name="notas_fiscais")
    chave_acesso = models.CharField(max_length=44)
    modelo = models.CharField(max_length=2)
    numero = models.CharField(max_length=20)
    serie = models.CharField(max_length=10)
    data_emissao = models.DateTimeField()
    natureza_operacao = models.CharField(max_length=255, blank=True)
    emitente_cnpj = models.CharField(max_length=14)
    emitente_nome = models.CharField(max_length=255)
    destinatario_cnpj = models.CharField(max_length=14)
    destinatario_nome = models.CharField(max_length=255)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    status_fiscal = models.CharField(max_length=20, choices=StatusFiscal.choices, default=StatusFiscal.FATURADA)
    status_conferencia = models.CharField(
        max_length=30,
        choices=StatusConferencia.choices,
        default=StatusConferencia.AGUARDANDO_APROVACAO,
    )
    status_recebimento = models.CharField(
        max_length=35,
        choices=StatusRecebimento.choices,
        default=StatusRecebimento.AGUARDANDO_RECEBIMENTO,
    )
    situacao_fila = models.CharField(max_length=30, choices=SituacaoFila.choices, default=SituacaoFila.AGUARDANDO_MATCH)
    criada_em = models.DateTimeField(auto_now_add=True)

    IMMUTABLE_FIELDS = {
        "arquivo_xml_id",
        "fornecedor_id",
        "loja_id",
        "chave_acesso",
        "modelo",
        "numero",
        "serie",
        "data_emissao",
        "natureza_operacao",
        "emitente_cnpj",
        "emitente_nome",
        "destinatario_cnpj",
        "destinatario_nome",
        "valor_total",
    }

    class Meta:
        verbose_name = "nota fiscal"
        verbose_name_plural = "notas fiscais"
        ordering = ["-data_emissao", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["empresa_cliente", "chave_acesso"], name="uniq_nf_chave_empresa"),
        ]
        indexes = [
            models.Index(fields=["empresa_cliente", "fornecedor", "loja", "status_conferencia"], name="nf_emp_forn_loja_conf_idx"),
            models.Index(fields=["empresa_cliente", "numero", "serie"], name="nf_emp_num_serie_idx"),
        ]

    def clean(self):
        super().clean()
        if self.pk:
            original = NotaFiscal.objects.get(pk=self.pk)
            changed = [
                field
                for field in self.IMMUTABLE_FIELDS
                if getattr(original, field) != getattr(self, field)
            ]
            if changed:
                raise ValidationError("Dados fiscais extraidos do XML sao imutaveis.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"NF {self.numero}/{self.serie}"


class ItemNotaFiscal(models.Model):
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.PROTECT, related_name="itens")
    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="itens_nota_fiscal")
    numero_item = models.PositiveIntegerField()
    codigo_original = models.CharField(max_length=120)
    codigo_normalizado = models.CharField(max_length=120, db_index=True)
    descricao_original = models.CharField(max_length=255)
    descricao_normalizada = models.CharField(max_length=255)
    ean_original = models.CharField(max_length=40, blank=True)
    ncm = models.CharField(max_length=20, blank=True)
    cfop = models.CharField(max_length=10, blank=True)
    unidade_original = models.CharField(max_length=40)
    unidade_normalizada = models.CharField(max_length=40)
    quantidade_original = models.CharField(max_length=80)
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    valor_unitario_original = models.CharField(max_length=80, blank=True)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    valor_produto_original = models.CharField(max_length=80, blank=True)
    valor_produto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    xped_original = models.CharField(max_length=80, blank=True)
    nitemped_original = models.CharField(max_length=20, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "item de nota fiscal"
        verbose_name_plural = "itens de nota fiscal"
        ordering = ["nota_fiscal_id", "numero_item"]
        constraints = [
            models.UniqueConstraint(fields=["nota_fiscal", "numero_item"], name="uniq_item_nf_numero"),
        ]
        indexes = [
            models.Index(fields=["empresa_cliente", "codigo_normalizado"], name="itnf_emp_cod_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("Itens fiscais extraidos do XML sao imutaveis.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.numero_item} - {self.codigo_original}"

from django.conf import settings
from django.db import models
from django.db.models import Q

from invoices.models import NotaFiscal
from organizations.models import EmpresaCliente


class Recebimento(models.Model):
    class Resultado(models.TextChoices):
        SEM_DIVERGENCIA = "SEM_DIVERGENCIA", "Sem divergencia"
        COM_DIVERGENCIA = "COM_DIVERGENCIA", "Com divergencia"

    class Status(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        ANULADO = "ANULADO", "Anulado"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="recebimentos")
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.PROTECT, related_name="recebimentos")
    resultado = models.CharField(max_length=30, choices=Resultado.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VIGENTE)
    data_recebimento = models.DateField()
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recebimentos_confirmados",
    )
    confirmado_em = models.DateTimeField(auto_now_add=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recebimentos_anulados",
    )
    anulada_em = models.DateTimeField(null=True, blank=True)
    justificativa_anulacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "recebimento"
        verbose_name_plural = "recebimentos"
        ordering = ["-confirmado_em", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["nota_fiscal"],
                condition=Q(status="VIGENTE"),
                name="uniq_receb_vigente_nf",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa_cliente", "status", "data_recebimento"], name="rec_emp_status_data_idx"),
        ]

    def __str__(self) -> str:
        return f"Recebimento {self.nota_fiscal} - {self.get_resultado_display()}"


class OcorrenciaRecebimento(models.Model):
    class Tipo(models.TextChoices):
        FALTA = "FALTA", "Falta"
        AVARIA = "AVARIA", "Avaria"
        QUANTIDADE_DIVERGENTE = "QUANTIDADE_DIVERGENTE", "Quantidade divergente"
        PRODUTO_DIVERGENTE = "PRODUTO_DIVERGENTE", "Produto divergente"
        OUTRO = "OUTRO", "Outro"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="ocorrencias_recebimento")
    recebimento = models.ForeignKey(Recebimento, on_delete=models.PROTECT, related_name="ocorrencias")
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.PROTECT, related_name="ocorrencias_recebimento")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    descricao = models.TextField()
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ocorrencias_recebimento_registradas",
    )
    registrada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ocorrencia de recebimento"
        verbose_name_plural = "ocorrencias de recebimento"
        ordering = ["-registrada_em", "-id"]
        indexes = [
            models.Index(fields=["empresa_cliente", "tipo", "registrada_em"], name="ocrec_emp_tipo_data_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.nota_fiscal}"

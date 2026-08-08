from django.conf import settings
from django.db import models

from approvals.models import Associacao
from files.models import Arquivo
from organizations.models import EmpresaCliente


class Exportacao(models.Model):
    class Tipo(models.TextChoices):
        COPIA_PREENCHIDA = "COPIA_PREENCHIDA", "Copia preenchida"
        HISTORICO = "HISTORICO", "Historico"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="exportacoes")
    associacao = models.ForeignKey(
        Associacao,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="exportacoes",
    )
    arquivo = models.OneToOneField(Arquivo, on_delete=models.PROTECT, related_name="exportacao")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    gerada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exportacoes_geradas",
    )
    gerada_em = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "exportacao"
        verbose_name_plural = "exportacoes"
        ordering = ["-gerada_em", "-id"]
        indexes = [
            models.Index(fields=["empresa_cliente", "tipo", "gerada_em"], name="export_emp_tipo_data_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} {self.gerada_em:%Y-%m-%d}"

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from organizations.models import EmpresaCliente


class EventoAuditoria(models.Model):
    class Origem(models.TextChoices):
        USUARIO = "USUARIO", "Usuario"
        SISTEMA = "SISTEMA", "Sistema"
        WORKER = "WORKER", "Worker"

    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
    )
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.USUARIO)
    sessao = models.CharField(max_length=120, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    entidade_tipo = models.CharField(max_length=120)
    entidade_id = models.CharField(max_length=80)
    acao = models.CharField(max_length=80)
    motivo = models.TextField(blank=True)
    antes = models.JSONField(null=True, blank=True)
    depois = models.JSONField(null=True, blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "evento de auditoria"
        verbose_name_plural = "eventos de auditoria"
        ordering = ["-criado_em", "-id"]
        indexes = [
            models.Index(
                fields=["empresa_cliente", "entidade_tipo", "entidade_id"],
                name="audit_ev_empresa_entidade_idx",
            ),
            models.Index(
                fields=["empresa_cliente", "acao", "criado_em"],
                name="audit_ev_empresa_acao_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("Eventos de auditoria sao imutaveis.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Eventos de auditoria nao podem ser excluidos.")

    def __str__(self) -> str:
        return f"{self.acao} {self.entidade_tipo}:{self.entidade_id}"

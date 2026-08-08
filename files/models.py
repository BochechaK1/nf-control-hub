from django.conf import settings
from django.db import models

from organizations.models import EmpresaCliente


class Arquivo(models.Model):
    class Tipo(models.TextChoices):
        PLANILHA_PEDIDO = "PLANILHA_PEDIDO", "Planilha de pedido"
        XML_NFE = "XML_NFE", "XML NF-e"
        PDF_DANFE = "PDF_DANFE", "PDF/DANFE"
        EXPORTACAO = "EXPORTACAO", "Exportacao"
        OUTRO = "OUTRO", "Outro"

    class Situacao(models.TextChoices):
        ARMAZENADO = "ARMAZENADO", "Armazenado"
        DUPLICADO = "DUPLICADO", "Duplicado"
        ERRO = "ERRO", "Erro"

    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="arquivos",
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    nome_original = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120, blank=True)
    tamanho = models.PositiveBigIntegerField()
    hash_sha256 = models.CharField(max_length=64, db_index=True)
    caminho_relativo = models.CharField(max_length=500)
    usuario_importacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arquivos_importados",
    )
    importado_em = models.DateTimeField(auto_now_add=True)
    situacao = models.CharField(max_length=20, choices=Situacao.choices, default=Situacao.ARMAZENADO)
    politica_retencao = models.CharField(max_length=80, default="PADRAO_MVP")

    class Meta:
        verbose_name = "arquivo"
        verbose_name_plural = "arquivos"
        ordering = ["-importado_em", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_cliente", "tipo", "hash_sha256"],
                name="uniq_arquivo_hash_empresa_tipo",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa_cliente", "tipo", "importado_em"], name="arquivo_emp_tipo_data_idx"),
        ]

    def __str__(self) -> str:
        return self.nome_original

from django.conf import settings
from django.db import models

from files.models import Arquivo
from organizations.models import EmpresaCliente


class Diagnostico(models.Model):
    class Tipo(models.TextChoices):
        PLANILHA_ILEGIVEL = "PLANILHA_ILEGIVEL", "Planilha ilegivel"
        ESTRUTURA_NAO_RECONHECIDA = "ESTRUTURA_NAO_RECONHECIDA", "Estrutura nao reconhecida"
        DOCUMENTO_NAO_SUPORTADO = "DOCUMENTO_NAO_SUPORTADO", "Documento nao suportado"
        CHAVE_DIVERGENTE = "CHAVE_DIVERGENTE", "Chave divergente"
        LINHA_INVALIDA = "LINHA_INVALIDA", "Linha invalida"
        DUPLICIDADE = "DUPLICIDADE", "Duplicidade"
        ERRO_PROCESSAMENTO = "ERRO_PROCESSAMENTO", "Erro de processamento"

    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        RESOLVIDO = "RESOLVIDO", "Resolvido"

    class Severidade(models.TextChoices):
        INFO = "INFO", "Informacao"
        ALERTA = "ALERTA", "Alerta"
        ERRO = "ERRO", "Erro"

    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="diagnosticos",
    )
    arquivo = models.ForeignKey(
        Arquivo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="diagnosticos",
    )
    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTO)
    severidade = models.CharField(max_length=20, choices=Severidade.choices, default=Severidade.ERRO)
    mensagem_usuario = models.CharField(max_length=255)
    detalhe_tecnico = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diagnosticos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "diagnostico"
        verbose_name_plural = "diagnosticos"
        ordering = ["-criado_em", "-id"]
        indexes = [
            models.Index(fields=["empresa_cliente", "status", "tipo"], name="diag_empresa_status_tipo_idx"),
        ]

    def __str__(self) -> str:
        return self.mensagem_usuario


class TarefaProcessamento(models.Model):
    class Tipo(models.TextChoices):
        IMPORTAR_PLANILHA = "IMPORTAR_PLANILHA", "Importar planilha"
        IMPORTAR_XML = "IMPORTAR_XML", "Importar XML"

    class Estado(models.TextChoices):
        AGUARDANDO = "AGUARDANDO", "Aguardando"
        PROCESSANDO = "PROCESSANDO", "Processando"
        CONCLUIDO = "CONCLUIDO", "Concluido"
        ERRO = "ERRO", "Erro"
        CANCELADO = "CANCELADO", "Cancelado"

    empresa_cliente = models.ForeignKey(EmpresaCliente, on_delete=models.PROTECT, related_name="tarefas")
    arquivo = models.ForeignKey(Arquivo, on_delete=models.PROTECT, related_name="tarefas")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.AGUARDANDO)
    tentativas = models.PositiveSmallIntegerField(default=0)
    max_tentativas = models.PositiveSmallIntegerField(default=3)
    progresso = models.PositiveSmallIntegerField(default=0)
    mensagem_usuario = models.CharField(max_length=255, blank=True)
    erro_tecnico = models.TextField(blank=True)
    heartbeat_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tarefa de processamento"
        verbose_name_plural = "tarefas de processamento"
        ordering = ["criada_em", "id"]
        constraints = [
            models.UniqueConstraint(fields=["tipo", "arquivo"], name="uniq_tarefa_tipo_arquivo"),
        ]
        indexes = [
            models.Index(fields=["estado", "criada_em"], name="tarefa_estado_criada_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} {self.arquivo_id}"

from django.contrib import admin

from .models import Diagnostico, TarefaProcessamento


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ("mensagem_usuario", "empresa_cliente", "tipo", "status", "severidade", "criado_em")
    list_filter = ("empresa_cliente", "tipo", "status", "severidade", "criado_em")
    search_fields = ("mensagem_usuario", "detalhe_tecnico", "arquivo__nome_original")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(TarefaProcessamento)
class TarefaProcessamentoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "arquivo", "estado", "progresso", "tentativas", "criada_em")
    list_filter = ("tipo", "estado", "empresa_cliente")
    search_fields = ("arquivo__nome_original", "mensagem_usuario", "erro_tecnico")
    readonly_fields = ("criada_em", "atualizada_em")

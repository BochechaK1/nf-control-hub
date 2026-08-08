from django.contrib import admin

from .models import OcorrenciaRecebimento, Recebimento


@admin.register(Recebimento)
class RecebimentoAdmin(admin.ModelAdmin):
    list_display = ("nota_fiscal", "resultado", "status", "data_recebimento", "confirmado_por", "confirmado_em")
    list_filter = ("resultado", "status", "data_recebimento")
    search_fields = ("nota_fiscal__numero", "nota_fiscal__chave_acesso")
    readonly_fields = ("confirmado_em", "anulada_em")


@admin.register(OcorrenciaRecebimento)
class OcorrenciaRecebimentoAdmin(admin.ModelAdmin):
    list_display = ("nota_fiscal", "tipo", "registrada_por", "registrada_em")
    list_filter = ("tipo",)
    search_fields = ("nota_fiscal__numero", "descricao")
    readonly_fields = ("registrada_em",)

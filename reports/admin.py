from django.contrib import admin

from .models import Exportacao


@admin.register(Exportacao)
class ExportacaoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "empresa_cliente", "associacao", "arquivo", "gerada_por", "gerada_em")
    list_filter = ("empresa_cliente", "tipo", "gerada_em")
    search_fields = ("arquivo__nome_original", "associacao__nota_fiscal__numero", "associacao__pedido__numero_pedido")
    readonly_fields = ("gerada_em",)

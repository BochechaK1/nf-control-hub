from django.contrib import admin

from .models import Conferencia, ConferenciaCandidata, ConferenciaItem


class ConferenciaItemInline(admin.TabularInline):
    model = ConferenciaItem
    extra = 0
    readonly_fields = (
        "item_nota_fiscal",
        "item_pedido",
        "resultado",
        "quantidade_nf",
        "saldo_pedido",
        "quantidade_cabe",
        "excesso",
        "alertas",
        "observacao",
        "ordem",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conferencia)
class ConferenciaAdmin(admin.ModelAdmin):
    list_display = ("nota_fiscal", "empresa_cliente", "vigente", "mensagem", "criada_em")
    list_filter = ("empresa_cliente", "vigente", "criada_em")
    search_fields = ("nota_fiscal__numero", "nota_fiscal__chave_acesso", "mensagem")
    readonly_fields = ("criada_em",)


@admin.register(ConferenciaCandidata)
class ConferenciaCandidataAdmin(admin.ModelAdmin):
    list_display = ("conferencia", "pedido", "compatibilidade", "nivel", "ambigua", "ordem")
    list_filter = ("nivel", "ambigua", "conferencia__empresa_cliente")
    search_fields = ("pedido__numero_pedido", "conferencia__nota_fiscal__numero")
    inlines = (ConferenciaItemInline,)


@admin.register(ConferenciaItem)
class ConferenciaItemAdmin(admin.ModelAdmin):
    list_display = ("candidata", "resultado", "item_nota_fiscal", "item_pedido", "quantidade_nf", "saldo_pedido", "excesso")
    list_filter = ("resultado",)
    search_fields = ("item_nota_fiscal__codigo_original", "item_pedido__codigo_original", "observacao")

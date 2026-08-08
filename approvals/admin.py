from django.contrib import admin

from .models import Alocacao, Associacao


class AlocacaoInline(admin.TabularInline):
    model = Alocacao
    extra = 0
    readonly_fields = ("item_nota_fiscal", "item_pedido", "quantidade", "status", "criada_em", "anulada_em")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Associacao)
class AssociacaoAdmin(admin.ModelAdmin):
    list_display = ("nota_fiscal", "pedido", "status", "aprovada_por", "aprovada_em")
    list_filter = ("empresa_cliente", "status", "aprovada_em")
    search_fields = ("nota_fiscal__numero", "nota_fiscal__chave_acesso", "pedido__numero_pedido", "justificativa")
    readonly_fields = ("aprovada_em", "anulada_em")
    inlines = (AlocacaoInline,)


@admin.register(Alocacao)
class AlocacaoAdmin(admin.ModelAdmin):
    list_display = ("associacao", "item_nota_fiscal", "item_pedido", "quantidade", "status")
    list_filter = ("empresa_cliente", "status")
    search_fields = ("associacao__nota_fiscal__numero", "item_pedido__codigo_original", "item_nota_fiscal__codigo_original")
    readonly_fields = ("criada_em", "anulada_em")

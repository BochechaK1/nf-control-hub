from django.contrib import admin

from .models import ItemPedido, ModeloPlanilha, ModeloPlanilhaVersao, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = (
        "empresa_cliente",
        "fornecedor",
        "aba",
        "linha",
        "codigo_original",
        "codigo_normalizado",
        "produto_original",
        "quantidade_original",
        "quantidade_pedida",
        "unidade_original",
        "saldo_cache",
        "faturado_cache",
        "recebido_cache",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero_pedido", "loja", "fornecedor", "estado", "data_operacional", "criado_em")
    list_filter = ("empresa_cliente", "loja", "fornecedor", "estado")
    search_fields = ("numero_pedido", "arquivo__nome_original", "itens__codigo_original", "itens__produto_original")
    readonly_fields = ("id", "arquivo", "criado_em")
    inlines = (ItemPedidoInline,)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "linha", "codigo_original", "produto_original", "quantidade_pedida", "saldo_cache")
    list_filter = ("empresa_cliente", "fornecedor", "unidade_normalizada")
    search_fields = ("codigo_original", "codigo_normalizado", "produto_original", "produto_normalizado")
    readonly_fields = ("criado_em",)


@admin.register(ModeloPlanilha)
class ModeloPlanilhaAdmin(admin.ModelAdmin):
    list_display = ("nome", "empresa_cliente", "fornecedor", "ativo", "criado_em")
    list_filter = ("empresa_cliente", "fornecedor", "ativo")
    search_fields = ("nome",)


@admin.register(ModeloPlanilhaVersao)
class ModeloPlanilhaVersaoAdmin(admin.ModelAdmin):
    list_display = ("modelo", "versao", "ativa", "criada_em")
    list_filter = ("modelo", "ativa")

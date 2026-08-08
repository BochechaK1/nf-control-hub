from django.contrib import admin

from .models import ItemNotaFiscal, NotaFiscal


class ItemNotaFiscalInline(admin.TabularInline):
    model = ItemNotaFiscal
    extra = 0
    readonly_fields = (
        "numero_item",
        "codigo_original",
        "codigo_normalizado",
        "descricao_original",
        "unidade_original",
        "quantidade_original",
        "quantidade",
        "valor_produto",
        "xped_original",
        "nitemped_original",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ("numero", "serie", "fornecedor", "loja", "status_conferencia", "situacao_fila", "data_emissao")
    list_filter = ("empresa_cliente", "fornecedor", "loja", "status_fiscal", "status_conferencia", "situacao_fila")
    search_fields = ("chave_acesso", "numero", "emitente_nome", "destinatario_nome", "itens__codigo_original")
    readonly_fields = (
        "arquivo_xml",
        "chave_acesso",
        "modelo",
        "numero",
        "serie",
        "data_emissao",
        "natureza_operacao",
        "emitente_cnpj",
        "emitente_nome",
        "destinatario_cnpj",
        "destinatario_nome",
        "valor_total",
        "criada_em",
    )
    inlines = (ItemNotaFiscalInline,)


@admin.register(ItemNotaFiscal)
class ItemNotaFiscalAdmin(admin.ModelAdmin):
    list_display = ("nota_fiscal", "numero_item", "codigo_original", "descricao_original", "quantidade", "unidade_original")
    list_filter = ("empresa_cliente", "unidade_normalizada", "cfop")
    search_fields = ("codigo_original", "codigo_normalizado", "descricao_original", "xped_original")
    readonly_fields = ("criado_em",)

from django.contrib import admin

from .models import EmpresaCliente, Fornecedor, Loja


@admin.register(EmpresaCliente)
class EmpresaClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "cnpj_normalizado", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome", "codigo", "cnpj", "cnpj_normalizado")
    readonly_fields = ("cnpj_normalizado", "criada_em", "atualizada_em")


@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "empresa_cliente", "cnpj_normalizado", "ativa")
    list_filter = ("empresa_cliente", "ativa")
    search_fields = ("nome", "codigo", "cnpj", "cnpj_normalizado")
    readonly_fields = ("cnpj_normalizado", "criada_em", "atualizada_em")


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "empresa_cliente", "cnpj_normalizado", "ativo")
    list_filter = ("empresa_cliente", "ativo")
    search_fields = ("nome", "cnpj", "cnpj_normalizado")
    readonly_fields = ("cnpj_normalizado", "criado_em", "atualizado_em")

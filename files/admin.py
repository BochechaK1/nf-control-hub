from django.contrib import admin

from .models import Arquivo


@admin.register(Arquivo)
class ArquivoAdmin(admin.ModelAdmin):
    list_display = ("nome_original", "empresa_cliente", "tipo", "situacao", "tamanho", "importado_em")
    list_filter = ("empresa_cliente", "tipo", "situacao", "importado_em")
    search_fields = ("nome_original", "hash_sha256", "caminho_relativo")
    readonly_fields = (
        "hash_sha256",
        "tamanho",
        "caminho_relativo",
        "usuario_importacao",
        "importado_em",
    )

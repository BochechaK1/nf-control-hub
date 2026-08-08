from django.contrib import admin

from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "empresa_cliente", "acao", "entidade_tipo", "entidade_id", "usuario", "origem")
    list_filter = ("empresa_cliente", "acao", "origem", "criado_em")
    search_fields = ("entidade_tipo", "entidade_id", "acao", "motivo", "usuario__username")
    readonly_fields = (
        "empresa_cliente",
        "usuario",
        "origem",
        "sessao",
        "ip_origem",
        "entidade_tipo",
        "entidade_id",
        "acao",
        "motivo",
        "antes",
        "depois",
        "metadados",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

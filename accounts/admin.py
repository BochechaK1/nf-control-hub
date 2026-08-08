from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied

from .models import Usuario, UsuarioLoja


class UsuarioLojaInline(admin.TabularInline):
    model = UsuarioLoja
    extra = 0
    autocomplete_fields = ("loja",)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("NF Control Hub", {"fields": ("role", "empresa_cliente", "deve_trocar_senha")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("NF Control Hub", {"fields": ("role", "empresa_cliente", "deve_trocar_senha")}),
    )
    list_display = ("username", "email", "role", "empresa_cliente", "is_active", "is_staff")
    list_filter = ("role", "empresa_cliente", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    autocomplete_fields = ("empresa_cliente",)
    inlines = (UsuarioLojaInline,)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if obj.role == Usuario.Role.MESTRE or obj.is_superuser:
                raise PermissionDenied("Apenas superusuarios podem conceder perfil Mestre ou superusuario.")
        super().save_model(request, obj, form, change)


@admin.register(UsuarioLoja)
class UsuarioLojaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "loja", "ativo")
    list_filter = ("ativo", "loja__empresa_cliente")
    search_fields = ("usuario__username", "loja__nome", "loja__codigo")
    autocomplete_fields = ("usuario", "loja")

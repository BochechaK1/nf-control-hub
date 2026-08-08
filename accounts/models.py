from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from organizations.models import EmpresaCliente, Loja

from .managers import UsuarioManager


class Usuario(AbstractUser):
    class Role(models.TextChoices):
        MESTRE = "MESTRE", "Mestre"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        VISUALIZADOR = "VISUALIZADOR", "Visualizador"

    role = models.CharField(
        "perfil",
        max_length=20,
        choices=Role.choices,
        default=Role.VISUALIZADOR,
    )
    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    deve_trocar_senha = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]

    @property
    def is_mestre(self) -> bool:
        return self.role == self.Role.MESTRE

    @property
    def is_administrador(self) -> bool:
        return self.role == self.Role.ADMINISTRADOR

    @property
    def is_visualizador(self) -> bool:
        return self.role == self.Role.VISUALIZADOR

    def pode_administrar(self) -> bool:
        return self.is_active and self.role in {self.Role.MESTRE, self.Role.ADMINISTRADOR}

    def lojas_autorizadas(self):
        if self.is_mestre:
            return Loja.objects.filter(ativa=True)
        if self.is_administrador and self.empresa_cliente_id:
            return Loja.objects.filter(empresa_cliente_id=self.empresa_cliente_id, ativa=True)
        return Loja.objects.filter(usuarios_autorizados__usuario=self, usuarios_autorizados__ativo=True, ativa=True)

    def clean(self):
        super().clean()
        if self.role == self.Role.MESTRE and not self.is_superuser:
            raise ValidationError({"role": "O perfil MESTRE deve ser reservado a superusuarios."})
        if self.role != self.Role.MESTRE and self.empresa_cliente_id is None:
            raise ValidationError({"empresa_cliente": "Usuarios de cliente devem pertencer a uma empresa."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class UsuarioLoja(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="lojas_vinculadas",
    )
    loja = models.ForeignKey(
        Loja,
        on_delete=models.PROTECT,
        related_name="usuarios_autorizados",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "usuario loja"
        verbose_name_plural = "usuarios lojas"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "loja"], name="uniq_usuario_loja"),
        ]

    def clean(self):
        super().clean()
        if self.usuario_id and self.loja_id:
            if self.usuario.empresa_cliente_id and self.usuario.empresa_cliente_id != self.loja.empresa_cliente_id:
                raise ValidationError("Usuario e loja devem pertencer a mesma empresa cliente.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.usuario} -> {self.loja}"

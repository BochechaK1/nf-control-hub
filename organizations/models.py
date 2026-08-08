from django.core.validators import RegexValidator
from django.db import models


digits_validator = RegexValidator(r"^\d*$", "Use apenas digitos.")


def normalize_digits(value: str | None) -> str:
    return "".join(char for char in (value or "") if char.isdigit())


class EmpresaCliente(models.Model):
    nome = models.CharField(max_length=180)
    codigo = models.SlugField(max_length=80, unique=True)
    cnpj = models.CharField(max_length=32, blank=True)
    cnpj_normalizado = models.CharField(
        max_length=14,
        blank=True,
        validators=[digits_validator],
        db_index=True,
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "empresa cliente"
        verbose_name_plural = "empresas cliente"
        ordering = ["nome"]

    def save(self, *args, **kwargs):
        self.cnpj_normalizado = normalize_digits(self.cnpj)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome


class Loja(models.Model):
    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="lojas",
    )
    codigo = models.CharField(max_length=40)
    nome = models.CharField(max_length=180)
    cnpj = models.CharField(max_length=32, blank=True)
    cnpj_normalizado = models.CharField(
        max_length=14,
        blank=True,
        validators=[digits_validator],
        db_index=True,
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "loja"
        verbose_name_plural = "lojas"
        ordering = ["empresa_cliente__nome", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_cliente", "codigo"],
                name="uniq_loja_codigo_por_empresa",
            ),
        ]

    def save(self, *args, **kwargs):
        self.cnpj_normalizado = normalize_digits(self.cnpj)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.nome} ({self.empresa_cliente})"


class Fornecedor(models.Model):
    empresa_cliente = models.ForeignKey(
        EmpresaCliente,
        on_delete=models.PROTECT,
        related_name="fornecedores",
    )
    nome = models.CharField(max_length=180)
    cnpj = models.CharField(max_length=32)
    cnpj_normalizado = models.CharField(
        max_length=14,
        validators=[digits_validator],
        db_index=True,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"
        ordering = ["empresa_cliente__nome", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_cliente", "cnpj_normalizado"],
                name="uniq_forn_cnpj_empresa",
            ),
        ]

    def save(self, *args, **kwargs):
        self.cnpj_normalizado = normalize_digits(self.cnpj)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome

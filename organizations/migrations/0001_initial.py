import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmpresaCliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=180)),
                ("codigo", models.SlugField(max_length=80, unique=True)),
                ("cnpj", models.CharField(blank=True, max_length=32)),
                ("cnpj_normalizado", models.CharField(blank=True, db_index=True, max_length=14, validators=[django.core.validators.RegexValidator("^\\d*$", "Use apenas digitos.")])),
                ("ativa", models.BooleanField(default=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "empresa cliente",
                "verbose_name_plural": "empresas cliente",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Fornecedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=180)),
                ("cnpj", models.CharField(max_length=32)),
                ("cnpj_normalizado", models.CharField(db_index=True, max_length=14, validators=[django.core.validators.RegexValidator("^\\d*$", "Use apenas digitos.")])),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fornecedores", to="organizations.empresacliente")),
            ],
            options={
                "verbose_name": "fornecedor",
                "verbose_name_plural": "fornecedores",
                "ordering": ["empresa_cliente__nome", "nome"],
            },
        ),
        migrations.CreateModel(
            name="Loja",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=40)),
                ("nome", models.CharField(max_length=180)),
                ("cnpj", models.CharField(blank=True, max_length=32)),
                ("cnpj_normalizado", models.CharField(blank=True, db_index=True, max_length=14, validators=[django.core.validators.RegexValidator("^\\d*$", "Use apenas digitos.")])),
                ("ativa", models.BooleanField(default=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lojas", to="organizations.empresacliente")),
            ],
            options={
                "verbose_name": "loja",
                "verbose_name_plural": "lojas",
                "ordering": ["empresa_cliente__nome", "nome"],
            },
        ),
        migrations.AddConstraint(
            model_name="fornecedor",
            constraint=models.UniqueConstraint(fields=("empresa_cliente", "cnpj_normalizado"), name="uniq_forn_cnpj_empresa"),
        ),
        migrations.AddConstraint(
            model_name="loja",
            constraint=models.UniqueConstraint(fields=("empresa_cliente", "codigo"), name="uniq_loja_codigo_por_empresa"),
        ),
        migrations.AddConstraint(
            model_name="loja",
            constraint=models.UniqueConstraint(condition=~Q(("cnpj_normalizado", "")), fields=("empresa_cliente", "cnpj_normalizado"), name="uniq_loja_cnpj_empresa"),
        ),
    ]

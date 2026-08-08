import decimal
import uuid
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("files", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModeloPlanilha",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="modelos_planilha", to="organizations.empresacliente")),
                ("fornecedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="modelos_planilha", to="organizations.fornecedor")),
            ],
            options={
                "verbose_name": "modelo de planilha",
                "verbose_name_plural": "modelos de planilha",
            },
        ),
        migrations.CreateModel(
            name="ModeloPlanilhaVersao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("versao", models.PositiveIntegerField(default=1)),
                ("configuracao", models.JSONField(blank=True, default=dict)),
                ("ativa", models.BooleanField(default=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("modelo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="versoes", to="orders.modeloplanilha")),
            ],
            options={
                "verbose_name": "versao de modelo de planilha",
                "verbose_name_plural": "versoes de modelo de planilha",
            },
        ),
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("numero_pedido", models.CharField(blank=True, max_length=80)),
                ("data_operacional", models.DateField()),
                ("estado", models.CharField(choices=[("ABERTA", "Aberta"), ("PARCIALMENTE_FATURADA", "Parcialmente faturada"), ("FATURADA", "Faturada"), ("PARCIALMENTE_RECEBIDA", "Parcialmente recebida"), ("CONCLUIDA", "Concluida")], default="ABERTA", max_length=30)),
                ("removido", models.BooleanField(default=False)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("arquivo", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="pedido", to="files.arquivo")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="organizations.empresacliente")),
                ("fornecedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="organizations.fornecedor")),
                ("loja", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="organizations.loja")),
                ("modelo_versao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="orders.modeloplanilhaversao")),
            ],
            options={
                "verbose_name": "pedido",
                "verbose_name_plural": "pedidos",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ItemPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aba", models.CharField(max_length=120)),
                ("linha", models.PositiveIntegerField()),
                ("codigo_original", models.CharField(blank=True, max_length=120)),
                ("codigo_normalizado", models.CharField(blank=True, db_index=True, max_length=120)),
                ("produto_original", models.CharField(max_length=255)),
                ("produto_normalizado", models.CharField(max_length=255)),
                ("quantidade_original", models.CharField(max_length=80)),
                ("quantidade_pedida", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))])),
                ("unidade_original", models.CharField(blank=True, max_length=40)),
                ("unidade_normalizada", models.CharField(blank=True, max_length=40)),
                ("tamanho_original", models.CharField(blank=True, max_length=80)),
                ("tamanho_normalizado", models.CharField(blank=True, max_length=80)),
                ("preco_estimado_original", models.CharField(blank=True, max_length=80)),
                ("preco_estimado", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("saldo_cache", models.DecimalField(decimal_places=3, max_digits=14)),
                ("faturado_cache", models.DecimalField(decimal_places=3, default=decimal.Decimal("0"), max_digits=14)),
                ("recebido_cache", models.DecimalField(decimal_places=3, default=decimal.Decimal("0"), max_digits=14)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens_pedido", to="organizations.empresacliente")),
                ("fornecedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens_pedido", to="organizations.fornecedor")),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens", to="orders.pedido")),
            ],
            options={
                "verbose_name": "item de pedido",
                "verbose_name_plural": "itens de pedido",
                "ordering": ["pedido_id", "aba", "linha", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="modeloplanilha",
            constraint=models.UniqueConstraint(fields=("empresa_cliente", "fornecedor", "nome"), name="uniq_modelo_planilha_forn_nome"),
        ),
        migrations.AddConstraint(
            model_name="modeloplanilhaversao",
            constraint=models.UniqueConstraint(fields=("modelo", "versao"), name="uniq_modelo_planilha_versao"),
        ),
        migrations.AddIndex(
            model_name="pedido",
            index=models.Index(fields=["empresa_cliente", "loja", "fornecedor", "estado"], name="ped_emp_loja_forn_est_idx"),
        ),
        migrations.AddConstraint(
            model_name="itempedido",
            constraint=models.UniqueConstraint(fields=("pedido", "aba", "linha"), name="uniq_item_pedido_aba_linha"),
        ),
        migrations.AddIndex(
            model_name="itempedido",
            index=models.Index(fields=["empresa_cliente", "fornecedor", "codigo_normalizado"], name="itped_emp_forn_cod_idx"),
        ),
    ]

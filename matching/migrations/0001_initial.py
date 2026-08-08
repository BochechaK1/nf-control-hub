import decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("invoices", "0001_initial"),
        ("orders", "0001_initial"),
        ("organizations", "0002_remove_loja_unique_cnpj"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conferencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vigente", models.BooleanField(default=True)),
                ("mensagem", models.CharField(blank=True, max_length=255)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="conferencias", to="organizations.empresacliente")),
                ("nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="conferencias", to="invoices.notafiscal")),
            ],
            options={
                "verbose_name": "conferencia",
                "verbose_name_plural": "conferencias",
                "ordering": ["-criada_em", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ConferenciaCandidata",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cobertura_itens", models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))])),
                ("cobertura_quantidades", models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))])),
                ("compatibilidade", models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))])),
                ("nivel", models.CharField(choices=[("ALTA", "Alta"), ("MEDIA", "Media"), ("BAIXA", "Baixa")], max_length=10)),
                ("ambigua", models.BooleanField(default=False)),
                ("alertas", models.JSONField(blank=True, default=list)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("conferencia", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="candidatas", to="matching.conferencia")),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="conferencias_candidatas", to="orders.pedido")),
            ],
            options={
                "verbose_name": "candidata de conferencia",
                "verbose_name_plural": "candidatas de conferencia",
                "ordering": ["ordem", "-compatibilidade", "pedido__data_operacional", "pedido__criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ConferenciaItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resultado", models.CharField(choices=[("CONFIRMADO", "Confirmado"), ("SUGESTAO_TEXTO", "Sugestao textual"), ("EXTRA_NF", "Extra na NF"), ("AUSENTE_NF", "Ausente na NF")], max_length=20)),
                ("quantidade_nf", models.DecimalField(decimal_places=4, default=decimal.Decimal("0"), max_digits=14)),
                ("saldo_pedido", models.DecimalField(decimal_places=4, default=decimal.Decimal("0"), max_digits=14)),
                ("quantidade_cabe", models.DecimalField(decimal_places=4, default=decimal.Decimal("0"), max_digits=14)),
                ("excesso", models.DecimalField(decimal_places=4, default=decimal.Decimal("0"), max_digits=14)),
                ("alertas", models.JSONField(blank=True, default=list)),
                ("observacao", models.CharField(blank=True, max_length=255)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("candidata", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens", to="matching.conferenciacandidata")),
                ("item_nota_fiscal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="conferencias_item", to="invoices.itemnotafiscal")),
                ("item_pedido", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="conferencias_item", to="orders.itempedido")),
            ],
            options={
                "verbose_name": "item de conferencia",
                "verbose_name_plural": "itens de conferencia",
                "ordering": ["ordem", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="conferencia",
            constraint=models.UniqueConstraint(condition=Q(("vigente", True)), fields=("nota_fiscal",), name="uniq_conf_vigente_nf"),
        ),
        migrations.AddConstraint(
            model_name="conferenciacandidata",
            constraint=models.UniqueConstraint(fields=("conferencia", "pedido"), name="uniq_conf_pedido"),
        ),
        migrations.AddIndex(
            model_name="conferenciaitem",
            index=models.Index(fields=["resultado"], name="confitem_resultado_idx"),
        ),
    ]

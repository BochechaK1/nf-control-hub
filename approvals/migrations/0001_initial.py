import decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("invoices", "0001_initial"),
        ("matching", "0001_initial"),
        ("orders", "0001_initial"),
        ("organizations", "0002_remove_loja_unique_cnpj"),
    ]

    operations = [
        migrations.CreateModel(
            name="Associacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("VIGENTE", "Vigente"), ("ANULADA", "Anulada")], default="VIGENTE", max_length=20)),
                ("aprovada_em", models.DateTimeField(auto_now_add=True)),
                ("justificativa", models.TextField(blank=True)),
                ("anulada_em", models.DateTimeField(blank=True, null=True)),
                ("justificativa_anulacao", models.TextField(blank=True)),
                ("aprovada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="associacoes_aprovadas", to=settings.AUTH_USER_MODEL)),
                ("candidata", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="associacoes", to="matching.conferenciacandidata")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="associacoes", to="organizations.empresacliente")),
                ("nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="associacoes", to="invoices.notafiscal")),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="associacoes", to="orders.pedido")),
                ("anulada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="associacoes_anuladas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "associacao",
                "verbose_name_plural": "associacoes",
                "ordering": ["-aprovada_em", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Alocacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade", models.DecimalField(decimal_places=4, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.0001"))])),
                ("status", models.CharField(choices=[("VIGENTE", "Vigente"), ("ANULADA", "Anulada")], default="VIGENTE", max_length=20)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("anulada_em", models.DateTimeField(blank=True, null=True)),
                ("associacao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alocacoes", to="approvals.associacao")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alocacoes", to="organizations.empresacliente")),
                ("item_nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alocacoes", to="invoices.itemnotafiscal")),
                ("item_pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alocacoes", to="orders.itempedido")),
            ],
            options={
                "verbose_name": "alocacao",
                "verbose_name_plural": "alocacoes",
                "ordering": ["associacao_id", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="associacao",
            constraint=models.UniqueConstraint(condition=Q(("status", "VIGENTE")), fields=("nota_fiscal",), name="uniq_assoc_vigente_nf"),
        ),
        migrations.AddIndex(
            model_name="alocacao",
            index=models.Index(fields=["empresa_cliente", "status"], name="aloc_emp_status_idx"),
        ),
        migrations.AddIndex(
            model_name="alocacao",
            index=models.Index(fields=["item_pedido", "status"], name="aloc_itemped_status_idx"),
        ),
        migrations.AddIndex(
            model_name="alocacao",
            index=models.Index(fields=["item_nota_fiscal", "status"], name="aloc_itemnf_status_idx"),
        ),
    ]

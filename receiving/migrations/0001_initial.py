from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("invoices", "0001_initial"),
        ("organizations", "0002_remove_loja_unique_cnpj"),
    ]

    operations = [
        migrations.CreateModel(
            name="Recebimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resultado", models.CharField(choices=[("SEM_DIVERGENCIA", "Sem divergencia"), ("COM_DIVERGENCIA", "Com divergencia")], max_length=30)),
                ("status", models.CharField(choices=[("VIGENTE", "Vigente"), ("ANULADO", "Anulado")], default="VIGENTE", max_length=20)),
                ("data_recebimento", models.DateField()),
                ("confirmado_em", models.DateTimeField(auto_now_add=True)),
                ("anulada_em", models.DateTimeField(blank=True, null=True)),
                ("justificativa_anulacao", models.TextField(blank=True)),
                ("anulada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="recebimentos_anulados", to=settings.AUTH_USER_MODEL)),
                ("confirmado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recebimentos_confirmados", to=settings.AUTH_USER_MODEL)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recebimentos", to="organizations.empresacliente")),
                ("nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recebimentos", to="invoices.notafiscal")),
            ],
            options={
                "verbose_name": "recebimento",
                "verbose_name_plural": "recebimentos",
                "ordering": ["-confirmado_em", "-id"],
            },
        ),
        migrations.CreateModel(
            name="OcorrenciaRecebimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("FALTA", "Falta"), ("AVARIA", "Avaria"), ("QUANTIDADE_DIVERGENTE", "Quantidade divergente"), ("PRODUTO_DIVERGENTE", "Produto divergente"), ("OUTRO", "Outro")], max_length=30)),
                ("descricao", models.TextField()),
                ("registrada_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ocorrencias_recebimento", to="organizations.empresacliente")),
                ("nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ocorrencias_recebimento", to="invoices.notafiscal")),
                ("recebimento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ocorrencias", to="receiving.recebimento")),
                ("registrada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ocorrencias_recebimento_registradas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "ocorrencia de recebimento",
                "verbose_name_plural": "ocorrencias de recebimento",
                "ordering": ["-registrada_em", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="recebimento",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "VIGENTE")), fields=("nota_fiscal",), name="uniq_receb_vigente_nf"),
        ),
        migrations.AddIndex(
            model_name="recebimento",
            index=models.Index(fields=["empresa_cliente", "status", "data_recebimento"], name="rec_emp_status_data_idx"),
        ),
        migrations.AddIndex(
            model_name="ocorrenciarecebimento",
            index=models.Index(fields=["empresa_cliente", "tipo", "registrada_em"], name="ocrec_emp_tipo_data_idx"),
        ),
    ]

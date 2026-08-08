from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("approvals", "0001_initial"),
        ("files", "0001_initial"),
        ("organizations", "0002_remove_loja_unique_cnpj"),
    ]

    operations = [
        migrations.CreateModel(
            name="Exportacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("COPIA_PREENCHIDA", "Copia preenchida"), ("HISTORICO", "Historico")], max_length=30)),
                ("gerada_em", models.DateTimeField(auto_now_add=True)),
                ("observacao", models.CharField(blank=True, max_length=255)),
                ("arquivo", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="exportacao", to="files.arquivo")),
                ("associacao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="exportacoes", to="approvals.associacao")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="exportacoes", to="organizations.empresacliente")),
                ("gerada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="exportacoes_geradas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "exportacao",
                "verbose_name_plural": "exportacoes",
                "ordering": ["-gerada_em", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="exportacao",
            index=models.Index(fields=["empresa_cliente", "tipo", "gerada_em"], name="export_emp_tipo_data_idx"),
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Arquivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("PLANILHA_PEDIDO", "Planilha de pedido"), ("XML_NFE", "XML NF-e"), ("PDF_DANFE", "PDF/DANFE"), ("EXPORTACAO", "Exportacao"), ("OUTRO", "Outro")], max_length=30)),
                ("nome_original", models.CharField(max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("tamanho", models.PositiveBigIntegerField()),
                ("hash_sha256", models.CharField(db_index=True, max_length=64)),
                ("caminho_relativo", models.CharField(max_length=500)),
                ("importado_em", models.DateTimeField(auto_now_add=True)),
                ("situacao", models.CharField(choices=[("ARMAZENADO", "Armazenado"), ("DUPLICADO", "Duplicado"), ("ERRO", "Erro")], default="ARMAZENADO", max_length=20)),
                ("politica_retencao", models.CharField(default="PADRAO_MVP", max_length=80)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="arquivos", to="organizations.empresacliente")),
                ("usuario_importacao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="arquivos_importados", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "arquivo",
                "verbose_name_plural": "arquivos",
                "ordering": ["-importado_em", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="arquivo",
            constraint=models.UniqueConstraint(fields=("empresa_cliente", "tipo", "hash_sha256"), name="uniq_arquivo_hash_empresa_tipo"),
        ),
        migrations.AddIndex(
            model_name="arquivo",
            index=models.Index(fields=["empresa_cliente", "tipo", "importado_em"], name="arquivo_emp_tipo_data_idx"),
        ),
    ]

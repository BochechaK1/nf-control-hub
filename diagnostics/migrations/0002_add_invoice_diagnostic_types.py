from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("diagnostics", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="diagnostico",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("PLANILHA_ILEGIVEL", "Planilha ilegivel"),
                    ("ESTRUTURA_NAO_RECONHECIDA", "Estrutura nao reconhecida"),
                    ("DOCUMENTO_NAO_SUPORTADO", "Documento nao suportado"),
                    ("CHAVE_DIVERGENTE", "Chave divergente"),
                    ("LINHA_INVALIDA", "Linha invalida"),
                    ("DUPLICIDADE", "Duplicidade"),
                    ("ERRO_PROCESSAMENTO", "Erro de processamento"),
                ],
                max_length=40,
            ),
        ),
    ]

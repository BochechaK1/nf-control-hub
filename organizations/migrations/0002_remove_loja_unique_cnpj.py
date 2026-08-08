from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="loja",
            name="uniq_loja_cnpj_empresa",
        ),
    ]

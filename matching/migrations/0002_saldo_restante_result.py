from django.db import migrations, models


def forward_saldo_restante(apps, schema_editor):
    ConferenciaCandidata = apps.get_model("matching", "ConferenciaCandidata")
    ConferenciaItem = apps.get_model("matching", "ConferenciaItem")

    for candidata in ConferenciaCandidata.objects.all():
        alertas = [alerta for alerta in (candidata.alertas or []) if alerta != "AUSENTE_NF"]
        if alertas != candidata.alertas:
            candidata.alertas = alertas
            candidata.save(update_fields=["alertas"])

    for item in ConferenciaItem.objects.filter(resultado="AUSENTE_NF"):
        item.resultado = "SALDO_RESTANTE"
        item.alertas = [alerta for alerta in (item.alertas or []) if alerta != "AUSENTE_NF"]
        item.observacao = "Item do pedido permanece em saldo para faturamento futuro."
        item.save(update_fields=["resultado", "alertas", "observacao"])


def reverse_saldo_restante(apps, schema_editor):
    ConferenciaItem = apps.get_model("matching", "ConferenciaItem")

    for item in ConferenciaItem.objects.filter(resultado="SALDO_RESTANTE"):
        item.resultado = "AUSENTE_NF"
        item.alertas = ["AUSENTE_NF"]
        item.observacao = "Item do pedido permanece em saldo."
        item.save(update_fields=["resultado", "alertas", "observacao"])


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conferenciaitem",
            name="resultado",
            field=models.CharField(
                choices=[
                    ("CONFIRMADO", "Confirmado"),
                    ("SUGESTAO_TEXTO", "Sugestao textual"),
                    ("EXTRA_NF", "Extra na NF"),
                    ("SALDO_RESTANTE", "Saldo restante"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(forward_saldo_restante, reverse_saldo_restante),
    ]

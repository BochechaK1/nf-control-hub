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
            name="EventoAuditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origem", models.CharField(choices=[("USUARIO", "Usuario"), ("SISTEMA", "Sistema"), ("WORKER", "Worker")], default="USUARIO", max_length=20)),
                ("sessao", models.CharField(blank=True, max_length=120)),
                ("ip_origem", models.GenericIPAddressField(blank=True, null=True)),
                ("entidade_tipo", models.CharField(max_length=120)),
                ("entidade_id", models.CharField(max_length=80)),
                ("acao", models.CharField(max_length=80)),
                ("motivo", models.TextField(blank=True)),
                ("antes", models.JSONField(blank=True, null=True)),
                ("depois", models.JSONField(blank=True, null=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="eventos_auditoria", to="organizations.empresacliente")),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="eventos_auditoria", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "evento de auditoria",
                "verbose_name_plural": "eventos de auditoria",
                "ordering": ["-criado_em", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="eventoauditoria",
            index=models.Index(fields=["empresa_cliente", "entidade_tipo", "entidade_id"], name="audit_ev_empresa_entidade_idx"),
        ),
        migrations.AddIndex(
            model_name="eventoauditoria",
            index=models.Index(fields=["empresa_cliente", "acao", "criado_em"], name="audit_ev_empresa_acao_idx"),
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("files", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Diagnostico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("PLANILHA_ILEGIVEL", "Planilha ilegivel"), ("ESTRUTURA_NAO_RECONHECIDA", "Estrutura nao reconhecida"), ("LINHA_INVALIDA", "Linha invalida"), ("DUPLICIDADE", "Duplicidade"), ("ERRO_PROCESSAMENTO", "Erro de processamento")], max_length=40)),
                ("status", models.CharField(choices=[("ABERTO", "Aberto"), ("RESOLVIDO", "Resolvido")], default="ABERTO", max_length=20)),
                ("severidade", models.CharField(choices=[("INFO", "Informacao"), ("ALERTA", "Alerta"), ("ERRO", "Erro")], default="ERRO", max_length=20)),
                ("mensagem_usuario", models.CharField(max_length=255)),
                ("detalhe_tecnico", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("arquivo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="diagnosticos", to="files.arquivo")),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="diagnosticos_criados", to=settings.AUTH_USER_MODEL)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="diagnosticos", to="organizations.empresacliente")),
            ],
            options={
                "verbose_name": "diagnostico",
                "verbose_name_plural": "diagnosticos",
                "ordering": ["-criado_em", "-id"],
            },
        ),
        migrations.CreateModel(
            name="TarefaProcessamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("IMPORTAR_PLANILHA", "Importar planilha"), ("IMPORTAR_XML", "Importar XML")], max_length=30)),
                ("estado", models.CharField(choices=[("AGUARDANDO", "Aguardando"), ("PROCESSANDO", "Processando"), ("CONCLUIDO", "Concluido"), ("ERRO", "Erro"), ("CANCELADO", "Cancelado")], default="AGUARDANDO", max_length=20)),
                ("tentativas", models.PositiveSmallIntegerField(default=0)),
                ("max_tentativas", models.PositiveSmallIntegerField(default=3)),
                ("progresso", models.PositiveSmallIntegerField(default=0)),
                ("mensagem_usuario", models.CharField(blank=True, max_length=255)),
                ("erro_tecnico", models.TextField(blank=True)),
                ("heartbeat_em", models.DateTimeField(blank=True, null=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("arquivo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tarefas", to="files.arquivo")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tarefas", to="organizations.empresacliente")),
            ],
            options={
                "verbose_name": "tarefa de processamento",
                "verbose_name_plural": "tarefas de processamento",
                "ordering": ["criada_em", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="diagnostico",
            index=models.Index(fields=["empresa_cliente", "status", "tipo"], name="diag_empresa_status_tipo_idx"),
        ),
        migrations.AddConstraint(
            model_name="tarefaprocessamento",
            constraint=models.UniqueConstraint(fields=("tipo", "arquivo"), name="uniq_tarefa_tipo_arquivo"),
        ),
        migrations.AddIndex(
            model_name="tarefaprocessamento",
            index=models.Index(fields=["estado", "criada_em"], name="tarefa_estado_criada_idx"),
        ),
    ]

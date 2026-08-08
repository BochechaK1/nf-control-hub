import decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("files", "0001_initial"),
        ("organizations", "0002_remove_loja_unique_cnpj"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotaFiscal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave_acesso", models.CharField(max_length=44)),
                ("modelo", models.CharField(max_length=2)),
                ("numero", models.CharField(max_length=20)),
                ("serie", models.CharField(max_length=10)),
                ("data_emissao", models.DateTimeField()),
                ("natureza_operacao", models.CharField(blank=True, max_length=255)),
                ("emitente_cnpj", models.CharField(max_length=14)),
                ("emitente_nome", models.CharField(max_length=255)),
                ("destinatario_cnpj", models.CharField(max_length=14)),
                ("destinatario_nome", models.CharField(max_length=255)),
                ("valor_total", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=14)),
                ("status_fiscal", models.CharField(choices=[("FATURADA", "Faturada"), ("CANCELADA", "Cancelada")], default="FATURADA", max_length=20)),
                ("status_conferencia", models.CharField(choices=[("AGUARDANDO_APROVACAO", "Aguardando aprovacao"), ("APROVADA", "Aprovada"), ("REJEITADA", "Rejeitada"), ("ANULADA", "Anulada")], default="AGUARDANDO_APROVACAO", max_length=30)),
                ("status_recebimento", models.CharField(choices=[("AGUARDANDO_RECEBIMENTO", "Aguardando recebimento"), ("RECEBIDA_SEM_DIVERGENCIA", "Recebida sem divergencia"), ("RECEBIDA_COM_DIVERGENCIA", "Recebida com divergencia")], default="AGUARDANDO_RECEBIMENTO", max_length=35)),
                ("situacao_fila", models.CharField(choices=[("AGUARDANDO_MATCH", "Aguardando match"), ("LOJA_DESCONHECIDA", "Loja desconhecida"), ("LOJA_AMBIGUA", "Loja ambigua")], default="AGUARDANDO_MATCH", max_length=30)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("arquivo_xml", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="nota_fiscal", to="files.arquivo")),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="organizations.empresacliente")),
                ("fornecedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="organizations.fornecedor")),
                ("loja", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notas_fiscais", to="organizations.loja")),
            ],
            options={
                "verbose_name": "nota fiscal",
                "verbose_name_plural": "notas fiscais",
                "ordering": ["-data_emissao", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ItemNotaFiscal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero_item", models.PositiveIntegerField()),
                ("codigo_original", models.CharField(max_length=120)),
                ("codigo_normalizado", models.CharField(db_index=True, max_length=120)),
                ("descricao_original", models.CharField(max_length=255)),
                ("descricao_normalizada", models.CharField(max_length=255)),
                ("ean_original", models.CharField(blank=True, max_length=40)),
                ("ncm", models.CharField(blank=True, max_length=20)),
                ("cfop", models.CharField(blank=True, max_length=10)),
                ("unidade_original", models.CharField(max_length=40)),
                ("unidade_normalizada", models.CharField(max_length=40)),
                ("quantidade_original", models.CharField(max_length=80)),
                ("quantidade", models.DecimalField(decimal_places=4, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.0001"))])),
                ("valor_unitario_original", models.CharField(blank=True, max_length=80)),
                ("valor_unitario", models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True)),
                ("valor_produto_original", models.CharField(blank=True, max_length=80)),
                ("valor_produto", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("xped_original", models.CharField(blank=True, max_length=80)),
                ("nitemped_original", models.CharField(blank=True, max_length=20)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("empresa_cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens_nota_fiscal", to="organizations.empresacliente")),
                ("nota_fiscal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="itens", to="invoices.notafiscal")),
            ],
            options={
                "verbose_name": "item de nota fiscal",
                "verbose_name_plural": "itens de nota fiscal",
                "ordering": ["nota_fiscal_id", "numero_item"],
            },
        ),
        migrations.AddConstraint(
            model_name="notafiscal",
            constraint=models.UniqueConstraint(fields=("empresa_cliente", "chave_acesso"), name="uniq_nf_chave_empresa"),
        ),
        migrations.AddIndex(
            model_name="notafiscal",
            index=models.Index(fields=["empresa_cliente", "fornecedor", "loja", "status_conferencia"], name="nf_emp_forn_loja_conf_idx"),
        ),
        migrations.AddIndex(
            model_name="notafiscal",
            index=models.Index(fields=["empresa_cliente", "numero", "serie"], name="nf_emp_num_serie_idx"),
        ),
        migrations.AddConstraint(
            model_name="itemnotafiscal",
            constraint=models.UniqueConstraint(fields=("nota_fiscal", "numero_item"), name="uniq_item_nf_numero"),
        ),
        migrations.AddIndex(
            model_name="itemnotafiscal",
            index=models.Index(fields=["empresa_cliente", "codigo_normalizado"], name="itnf_emp_cod_idx"),
        ),
    ]

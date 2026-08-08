import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organizations.models import EmpresaCliente, Loja, normalize_digits


REQUIRED_COLUMNS = {"codigo", "nome", "cnpj"}


class Command(BaseCommand):
    help = "Importa ou atualiza lojas por arquivo CSV com codigo,nome,cnpj."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do CSV com colunas codigo,nome,cnpj.")
        parser.add_argument(
            "--empresa-codigo",
            help="Codigo da empresa cliente. Se omitido, usa a unica empresa ativa disponivel.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida o arquivo sem gravar alteracoes.",
        )

    def _resolve_company(self, empresa_codigo: str | None):
        if empresa_codigo:
            empresa = EmpresaCliente.objects.filter(codigo=empresa_codigo, ativa=True).first()
            if not empresa:
                raise CommandError(f"Empresa ativa nao encontrada: {empresa_codigo}")
            return empresa

        empresas = list(EmpresaCliente.objects.filter(ativa=True)[:2])
        if len(empresas) == 1:
            return empresas[0]
        raise CommandError("Informe --empresa-codigo quando houver zero ou mais de uma empresa ativa.")

    def handle(self, *args, **options):
        path = Path(options["arquivo"])
        if not path.exists():
            raise CommandError(f"Arquivo nao encontrado: {path}")

        empresa = self._resolve_company(options.get("empresa_codigo"))
        dry_run = options["dry_run"]
        created = 0
        updated = 0

        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = set(reader.fieldnames or [])
            missing_columns = REQUIRED_COLUMNS - columns
            if missing_columns:
                raise CommandError(f"Colunas obrigatorias ausentes: {', '.join(sorted(missing_columns))}")

            with transaction.atomic():
                for line_number, row in enumerate(reader, start=2):
                    codigo = (row.get("codigo") or "").strip()
                    nome = (row.get("nome") or "").strip()
                    cnpj = (row.get("cnpj") or "").strip()
                    cnpj_normalizado = normalize_digits(cnpj)
                    if not codigo or not nome or not cnpj_normalizado:
                        raise CommandError(f"Linha {line_number}: codigo, nome e cnpj sao obrigatorios.")
                    if len(cnpj_normalizado) != 14:
                        raise CommandError(f"Linha {line_number}: CNPJ deve ter 14 digitos.")

                    loja = Loja.objects.filter(
                        empresa_cliente=empresa,
                        cnpj_normalizado=cnpj_normalizado,
                    ).first()
                    if not loja:
                        loja = Loja.objects.filter(empresa_cliente=empresa, codigo=codigo).first()

                    if loja:
                        changed = False
                        if loja.nome != nome:
                            loja.nome = nome
                            changed = True
                        if loja.codigo != codigo:
                            loja.codigo = codigo
                            changed = True
                        if loja.cnpj != cnpj:
                            loja.cnpj = cnpj
                            changed = True
                        if not loja.ativa:
                            loja.ativa = True
                            changed = True
                        if changed:
                            loja.save(update_fields=["nome", "codigo", "cnpj", "cnpj_normalizado", "ativa", "atualizada_em"])
                            updated += 1
                    else:
                        Loja.objects.create(
                            empresa_cliente=empresa,
                            codigo=codigo,
                            nome=nome,
                            cnpj=cnpj,
                        )
                        created += 1

                if dry_run:
                    transaction.set_rollback(True)

        mode = "validacao" if dry_run else "importacao"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} concluida para {empresa.nome}: {created} criada(s), {updated} atualizada(s)."
            )
        )

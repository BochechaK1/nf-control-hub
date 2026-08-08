from django.core.management.base import BaseCommand

from organizations.models import EmpresaCliente, Fornecedor, Loja


class Command(BaseCommand):
    help = "Cria dados minimos para preview local do NF Control Hub."

    def handle(self, *args, **options):
        empresa, _ = EmpresaCliente.objects.get_or_create(
            codigo="destiny",
            defaults={"nome": "Destiny In", "cnpj": "12.345.678/0001-90"},
        )
        loja, _ = Loja.objects.get_or_create(
            empresa_cliente=empresa,
            codigo="matriz",
            defaults={"nome": "Matriz", "cnpj": "11.111.111/0001-11"},
        )
        fornecedor, _ = Fornecedor.objects.get_or_create(
            empresa_cliente=empresa,
            cnpj_normalizado="22222222000122",
            defaults={"nome": "Coral", "cnpj": "22.222.222/0001-22"},
        )

        self.stdout.write(self.style.SUCCESS(f"Empresa: {empresa.nome}"))
        self.stdout.write(self.style.SUCCESS(f"Loja: {loja.nome}"))
        self.stdout.write(self.style.SUCCESS(f"Fornecedor: {fornecedor.nome}"))

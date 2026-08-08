from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from invoices.models import NotaFiscal
from invoices.services import locate_store
from matching.services import recalcular_conferencia_para_nota
from orders.models import ItemPedido, ModeloPlanilha, ModeloPlanilhaVersao, Pedido
from organizations.models import Fornecedor, normalize_digits


class Command(BaseCommand):
    help = "Reidentifica lojas das NFs e recalcula conferencias da Fila."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapear-fornecedor",
            action="append",
            default=[],
            metavar="ALIAS=CNPJ",
            help="Move pedidos do fornecedor ALIAS para o fornecedor fiscal com CNPJ informado.",
        )

    def _apply_supplier_mapping(self, mapping: str) -> str:
        if "=" not in mapping:
            raise CommandError("Use --mapear-fornecedor no formato ALIAS=CNPJ.")
        alias_name, target_cnpj = [part.strip() for part in mapping.split("=", 1)]
        target_digits = normalize_digits(target_cnpj)
        if not alias_name or len(target_digits) != 14:
            raise CommandError("Alias e CNPJ com 14 digitos sao obrigatorios.")

        alias = Fornecedor.objects.filter(nome__iexact=alias_name).first()
        target = Fornecedor.objects.filter(cnpj_normalizado=target_digits).first()
        if not alias:
            raise CommandError(f"Fornecedor alias nao encontrado: {alias_name}")
        if not target:
            raise CommandError(f"Fornecedor fiscal nao encontrado para CNPJ: {target_cnpj}")
        if alias.id == target.id:
            return f"{alias_name}: ja aponta para {target.nome}."

        pedidos = Pedido.objects.filter(fornecedor=alias).update(fornecedor=target)
        itens = ItemPedido.objects.filter(fornecedor=alias).update(fornecedor=target)
        modelos = 0
        for source_model in list(ModeloPlanilha.objects.filter(fornecedor=alias).prefetch_related("versoes")):
            target_model = ModeloPlanilha.objects.filter(
                empresa_cliente=source_model.empresa_cliente,
                fornecedor=target,
                nome=source_model.nome,
            ).first()
            if target_model:
                for source_version in list(source_model.versoes.all()):
                    target_version, _ = ModeloPlanilhaVersao.objects.get_or_create(
                        modelo=target_model,
                        versao=source_version.versao,
                        defaults={
                            "configuracao": source_version.configuracao,
                            "ativa": source_version.ativa,
                        },
                    )
                    Pedido.objects.filter(modelo_versao=source_version).update(modelo_versao=target_version)
                    source_version.delete()
                source_model.delete()
            else:
                source_model.fornecedor = target
                source_model.save(update_fields=["fornecedor"])
            modelos += 1
        if alias_name.upper() not in target.nome.upper():
            target.nome = f"{target.nome} / {alias_name}"
            target.save(update_fields=["nome", "atualizado_em"])
        alias.ativo = False
        alias.save(update_fields=["ativo", "atualizado_em"])
        return f"{alias_name} -> {target.nome}: {pedidos} pedido(s), {itens} item(ns), {modelos} modelo(s)."

    def handle(self, *args, **options):
        with transaction.atomic():
            for mapping in options["mapear_fornecedor"]:
                self.stdout.write(self._apply_supplier_mapping(mapping))

            updated_stores = 0
            recalculated = 0
            for nota in NotaFiscal.objects.select_related("empresa_cliente"):
                loja, situacao = locate_store(
                    empresa_cliente=nota.empresa_cliente,
                    destinatario_cnpj=nota.destinatario_cnpj,
                )
                if nota.loja_id != (loja.id if loja else None) or nota.situacao_fila != situacao:
                    NotaFiscal.objects.filter(pk=nota.pk).update(loja=loja, situacao_fila=situacao)
                    nota.loja = loja
                    nota.situacao_fila = situacao
                    updated_stores += 1
                recalcular_conferencia_para_nota(nota)
                recalculated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Fila reprocessada: {updated_stores} NF(s) com loja atualizada, {recalculated} conferencia(s) recalculada(s)."
            )
        )

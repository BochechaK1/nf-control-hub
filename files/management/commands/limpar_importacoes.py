from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from approvals.models import Alocacao, Associacao
from diagnostics.models import Diagnostico, TarefaProcessamento
from files.models import Arquivo
from invoices.models import ItemNotaFiscal, NotaFiscal
from matching.models import Conferencia, ConferenciaCandidata, ConferenciaItem
from orders.models import ItemPedido, Pedido
from receiving.models import OcorrenciaRecebimento, Recebimento
from reports.models import Exportacao


class Command(BaseCommand):
    help = "Limpa importacoes de planilhas/XML e dados derivados, preservando cadastros e auditoria."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Executa a limpeza. Sem esta flag, roda apenas em simulacao.",
        )
        parser.add_argument(
            "--apagar-arquivos",
            action="store_true",
            help="Remove tambem os arquivos fisicos controlados pelo banco.",
        )

    def _target_files(self):
        import_files = Arquivo.objects.filter(tipo__in=[Arquivo.Tipo.PLANILHA_PEDIDO, Arquivo.Tipo.XML_NFE])
        export_file_ids = Exportacao.objects.values_list("arquivo_id", flat=True)
        return Arquivo.objects.filter(id__in=list(import_files.values_list("id", flat=True)) + list(export_file_ids))

    def _delete_queryset(self, label, queryset, deleted):
        count = queryset.count()
        if count:
            queryset.delete()
        deleted[label] = count

    def _safe_unlink(self, relative_path: str):
        root = settings.NFCH_STORAGE_ROOT.resolve()
        target = (settings.NFCH_STORAGE_ROOT / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise CommandError(f"Caminho fora do storage recusado: {target}") from exc
        if target.exists() and target.is_file():
            target.unlink()
            parent = target.parent
            while parent != root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
            return True
        return False

    def handle(self, *args, **options):
        confirmar = options["confirmar"]
        apagar_arquivos = options["apagar_arquivos"]
        target_files = self._target_files()
        file_paths = list(target_files.values_list("caminho_relativo", flat=True))
        deleted = {
            "arquivos_fisicos": 0,
        }

        preview = {
            "planilhas": Arquivo.objects.filter(tipo=Arquivo.Tipo.PLANILHA_PEDIDO).count(),
            "xmls": Arquivo.objects.filter(tipo=Arquivo.Tipo.XML_NFE).count(),
            "pedidos": Pedido.objects.count(),
            "notas": NotaFiscal.objects.count(),
            "diagnosticos": Diagnostico.objects.filter(arquivo__in=target_files).count(),
            "tarefas": TarefaProcessamento.objects.filter(arquivo__in=target_files).count(),
            "exportacoes": Exportacao.objects.count(),
        }
        self.stdout.write(f"Alvo da limpeza: {preview}")

        if not confirmar:
            self.stdout.write(self.style.WARNING("Simulacao concluida. Use --confirmar para executar."))
            return

        with transaction.atomic():
            self._delete_queryset("ocorrencias_recebimento", OcorrenciaRecebimento.objects.all(), deleted)
            self._delete_queryset("recebimentos", Recebimento.objects.all(), deleted)
            self._delete_queryset("exportacoes", Exportacao.objects.all(), deleted)
            self._delete_queryset("alocacoes", Alocacao.objects.all(), deleted)
            self._delete_queryset("associacoes", Associacao.objects.all(), deleted)
            self._delete_queryset("conferencia_itens", ConferenciaItem.objects.all(), deleted)
            self._delete_queryset("conferencia_candidatas", ConferenciaCandidata.objects.all(), deleted)
            self._delete_queryset("conferencias", Conferencia.objects.all(), deleted)
            self._delete_queryset("itens_nf", ItemNotaFiscal.objects.all(), deleted)
            self._delete_queryset("notas", NotaFiscal.objects.all(), deleted)
            self._delete_queryset("itens_pedido", ItemPedido.objects.all(), deleted)
            self._delete_queryset("pedidos", Pedido.objects.all(), deleted)
            self._delete_queryset("diagnosticos", Diagnostico.objects.filter(arquivo__in=target_files), deleted)
            self._delete_queryset("tarefas", TarefaProcessamento.objects.filter(arquivo__in=target_files), deleted)
            self._delete_queryset("arquivos", target_files, deleted)

        if apagar_arquivos:
            for relative_path in file_paths:
                if self._safe_unlink(relative_path):
                    deleted["arquivos_fisicos"] += 1

        self.stdout.write(self.style.SUCCESS(f"Limpeza concluida: {deleted}"))

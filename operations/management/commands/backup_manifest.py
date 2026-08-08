from pathlib import Path
import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Gera manifesto de hashes dos arquivos controlados. Nao substitui pg_dump."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="", help="Arquivo JSON de saida.")

    def handle(self, *args, **options):
        root = Path(settings.NFCH_STORAGE_ROOT)
        entries = []
        if root.exists():
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "size": path.stat().st_size,
                        "sha256": digest,
                    }
                )

        manifest = {
            "generated_at": timezone.now().isoformat(),
            "storage_root": str(root),
            "files": entries,
            "warning": "Este manifesto complementa o backup. O banco deve ser salvo com pg_dump consistente.",
        }
        output = options["output"]
        if output:
            Path(output).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"manifesto gerado: {output}"))
        else:
            self.stdout.write(json.dumps(manifest, indent=2))

from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import Client, TestCase, override_settings


class OperationsTests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = Client().get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_backup_manifest_command_runs(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "manifest.json"
            with override_settings(NFCH_STORAGE_ROOT=Path(tmp)):
                call_command("backup_manifest", output=str(output))

            self.assertTrue(output.exists())
            self.assertIn("pg_dump", output.read_text(encoding="utf-8"))

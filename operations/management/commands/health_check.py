from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Executa health check basico da aplicacao e do banco."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            raise CommandError(f"Banco indisponivel: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("health: ok"))

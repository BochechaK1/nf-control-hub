from django.db import connection
from django.http import JsonResponse


def health(request):
    checks = {"database": "ok"}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        checks["database"] = "erro"
        checks["database_error"] = exc.__class__.__name__
        status = 503
    return JsonResponse({"status": "ok" if status == 200 else "erro", "checks": checks}, status=status)

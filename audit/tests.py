from django.core.exceptions import ValidationError
from django.test import TestCase

from organizations.models import EmpresaCliente

from .services import registrar_evento


class EventoAuditoriaTests(TestCase):
    def test_event_is_append_only(self):
        empresa = EmpresaCliente.objects.create(nome="Cliente", codigo="cliente")
        evento = registrar_evento(
            empresa_cliente=empresa,
            entidade=empresa,
            acao="CRIAR_EMPRESA",
            motivo="teste",
        )

        evento.motivo = "alterado"
        with self.assertRaises(ValidationError):
            evento.save()

        with self.assertRaises(ValidationError):
            evento.delete()

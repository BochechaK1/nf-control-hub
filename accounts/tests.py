from django.core.exceptions import ValidationError
from django.test import TestCase

from organizations.models import EmpresaCliente, Loja

from .models import Usuario, UsuarioLoja


class UsuarioModelTests(TestCase):
    def setUp(self):
        self.empresa = EmpresaCliente.objects.create(nome="Cliente", codigo="cliente")
        self.loja = Loja.objects.create(empresa_cliente=self.empresa, codigo="matriz", nome="Matriz")

    def test_superuser_is_created_as_mestre(self):
        usuario = Usuario.objects.create_superuser(username="kauan", password="secret")

        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.is_staff)
        self.assertEqual(usuario.role, Usuario.Role.MESTRE)

    def test_mestre_requires_superuser(self):
        usuario = Usuario(username="mestre-comum", role=Usuario.Role.MESTRE)

        with self.assertRaises(ValidationError):
            usuario.save()

    def test_cliente_user_requires_empresa(self):
        usuario = Usuario(username="viewer", role=Usuario.Role.VISUALIZADOR)

        with self.assertRaises(ValidationError):
            usuario.save()

    def test_visualizador_sees_only_linked_stores(self):
        outra_loja = Loja.objects.create(empresa_cliente=self.empresa, codigo="filial", nome="Filial")
        usuario = Usuario.objects.create_user(
            username="viewer",
            password="secret",
            role=Usuario.Role.VISUALIZADOR,
            empresa_cliente=self.empresa,
        )
        UsuarioLoja.objects.create(usuario=usuario, loja=self.loja)

        self.assertQuerySetEqual(usuario.lojas_autorizadas(), [self.loja], transform=lambda obj: obj)
        self.assertNotIn(outra_loja, usuario.lojas_autorizadas())

    def test_administrador_sees_active_company_stores(self):
        usuario = Usuario.objects.create_user(
            username="admin",
            password="secret",
            role=Usuario.Role.ADMINISTRADOR,
            empresa_cliente=self.empresa,
        )

        self.assertQuerySetEqual(usuario.lojas_autorizadas(), [self.loja], transform=lambda obj: obj)
        self.assertTrue(usuario.pode_administrar())

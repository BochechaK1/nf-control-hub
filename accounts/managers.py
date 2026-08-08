from django.contrib.auth.models import UserManager


class UsuarioManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.MESTRE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuario deve ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuario deve ter is_superuser=True.")
        if extra_fields.get("role") != self.model.Role.MESTRE:
            raise ValueError("Superusuario deve usar perfil MESTRE.")

        return self._create_user(username, email, password, **extra_fields)

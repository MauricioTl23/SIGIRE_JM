from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Modelo personalizado de usuario del sistema.

    Hereda de AbstractUser, por lo tanto conserva las funcionalidades básicas
    de autenticación de Django, como:
    - username
    - password
    - email
    - first_name
    - last_name
    - is_active
    - is_staff
    - is_superuser

    Además, agrega campos propios para el contexto institucional:
    - cédula de identidad
    - complemento
    - expedido
    - celular
    - rol
    """

    class Roles(models.TextChoices):
        """
        Roles permitidos dentro del sistema.

        Estos valores permiten diferenciar los permisos o responsabilidades
        de cada usuario dentro de la institución.
        """

        DIRECTOR = "director", "Director(a)"
        SECRETARIA = "secretaria", "Secretaría"

    # Lista de departamentos válidos para el campo "expedido".
    DEPARTAMENTOS_CHOICES = [
        ("LP", "La Paz"),
        ("OR", "Oruro"),
        ("PT", "Potosí"),
        ("CB", "Cochabamba"),
        ("SC", "Santa Cruz"),
        ("BN", "Beni"),
        ("PA", "Pando"),
        ("TJ", "Tarija"),
        ("CH", "Chuquisaca"),
    ]

    # Cédula de identidad del usuario.
    # Se usa como clave primaria, por lo tanto identifica de forma única al usuario.
    cedula_identidad = models.CharField(
        max_length=20,
        unique=True,
        primary_key=True
    )

    # Complemento opcional de la cédula de identidad.
    # Ejemplo: 1A, 2B, etc.
    complemento = models.CharField(
        max_length=2,
        blank=True,
        null=True
    )

    # Departamento donde fue expedida la cédula de identidad.
    expedido = models.CharField(
        max_length=2,
        choices=DEPARTAMENTOS_CHOICES,
        blank=True,
        null=True
    )

    # Campos requeridos cuando se crea un superusuario desde consola.
    REQUIRED_FIELDS = [
        "email",
        "first_name",
        "last_name",
        "cedula_identidad",
    ]

    # Número de celular del usuario.
    celular = models.CharField(
        max_length=20
    )

    # Rol del usuario dentro del sistema.
    rol = models.CharField(
        max_length=15,
        choices=Roles.choices,
        default=Roles.SECRETARIA
    )

    def __str__(self):
        """
        Representación legible del usuario.

        Si el usuario tiene nombre y apellido, devuelve el nombre completo.
        Si no tiene esos datos, devuelve el username.
        """

        nombre_completo = f"{self.first_name} {self.last_name}".strip()

        return nombre_completo if nombre_completo else self.username

    class Meta:
        """
        Configuración de nombres visibles para el panel administrativo de Django.
        """

        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"


class LoginAttempt(models.Model):
    """
    Modelo para registrar intentos fallidos de inicio de sesión.

    Este modelo permite aplicar una política de seguridad progresiva:
    mientras más intentos fallidos tenga un usuario, mayor será el bloqueo.

    Se relaciona con el formulario SecureAuthenticationForm, donde se consulta
    y actualiza esta información durante el proceso de login.
    """

    # Nombre de usuario que intentó iniciar sesión.
    username = models.CharField(
        max_length=150,
        unique=True
    )

    # Cantidad de intentos fallidos acumulados.
    failed_attempts = models.PositiveIntegerField(
        default=0
    )

    # Fecha y hora hasta la cual el usuario queda bloqueado temporalmente.
    lock_until = models.DateTimeField(
        null=True,
        blank=True
    )

    # Indica si la cuenta fue bloqueada por superar el máximo de intentos.
    disabled_by_attempts = models.BooleanField(
        default=False
    )

    # Registra automáticamente la fecha y hora del último intento.
    last_attempt = models.DateTimeField(
        auto_now=True
    )

    def is_locked(self):
        """
        Verifica si el usuario todavía está bloqueado temporalmente.

        Retorna:
        - True si existe una fecha de bloqueo y todavía no ha expirado.
        - False si no existe bloqueo o si el tiempo de bloqueo ya terminó.
        """

        return self.lock_until and timezone.now() < self.lock_until

    def remaining_lock_seconds(self):
        """
        Calcula cuántos segundos faltan para que termine el bloqueo temporal.

        Retorna:
        - La cantidad de segundos restantes si el bloqueo sigue activo.
        - 0 si no existe bloqueo activo.
        """

        if self.lock_until and timezone.now() < self.lock_until:
            return int((self.lock_until - timezone.now()).total_seconds())

        return 0

    def register_failed_attempt(self):
        """
        Registra un intento fallido de inicio de sesión.

        Cada vez que el usuario falla al iniciar sesión, se incrementa el contador
        y se aplica una sanción progresiva según la cantidad de intentos.

        Reglas:
        - 3 intentos: bloqueo de 1 minuto.
        - 6 intentos: bloqueo de 5 minutos.
        - 9 intentos: bloqueo de 15 minutos.
        - 12 intentos: cuenta marcada como deshabilitada por intentos.
        """

        # Incrementa el contador de intentos fallidos.
        self.failed_attempts += 1

        # Si llega a 12 intentos, se marca como bloqueado por intentos.
        if self.failed_attempts >= 12:
            self.disabled_by_attempts = True

        # Si llega a 9 intentos, se bloquea por 15 minutos.
        elif self.failed_attempts >= 9:
            self.lock_until = timezone.now() + timedelta(minutes=15)

        # Si llega a 6 intentos, se bloquea por 5 minutos.
        elif self.failed_attempts >= 6:
            self.lock_until = timezone.now() + timedelta(minutes=5)

        # Si llega a 3 intentos, se bloquea por 1 minuto.
        elif self.failed_attempts >= 3:
            self.lock_until = timezone.now() + timedelta(minutes=1)

        # Guarda los cambios en la base de datos.
        self.save()

    def reset_attempts(self):
        """
        Reinicia los intentos fallidos del usuario.

        Se puede usar cuando:
        - El usuario inicia sesión correctamente.
        - Un administrador desbloquea la cuenta.
        - Se desea limpiar el historial de bloqueo.
        """

        self.failed_attempts = 0
        self.lock_until = None
        self.disabled_by_attempts = False

        self.save()

    def __str__(self):
        """
        Representación legible del registro de intentos.

        Útil para visualizar el objeto en el panel administrativo.
        """

        return f"{self.username} - intentos fallidos: {self.failed_attempts}"
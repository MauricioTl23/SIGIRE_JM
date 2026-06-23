import os
import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError

from .models import User, LoginAttempt


class LoginForm(AuthenticationForm):
    """
    Formulario básico de inicio de sesión.

    Hereda de AuthenticationForm de Django y solo personaliza la apariencia
    de los campos username y password usando la clase CSS 'form-control'.
    """

    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )


class RegistroPersonalForm(forms.ModelForm):
    """
    Formulario para registrar y editar usuarios del personal institucional.

    Este formulario trabaja con el modelo User y valida datos personales como:
    - nombres
    - apellidos
    - cédula de identidad
    - complemento
    - expedido
    - celular
    - rol
    - correo electrónico

    También evita que exista más de un director activo en el sistema.
    """

    # Opciones válidas para el lugar de expedición de la cédula de identidad.
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

    # Se obliga a registrar un correo electrónico válido.
    email = forms.EmailField(
        required=True,
        label="Correo Electrónico"
    )

    # Campo para seleccionar el departamento donde fue expedida la C.I.
    expedido = forms.ChoiceField(
        choices=DEPARTAMENTOS_CHOICES,
        label="Expedido en"
    )

    # Complemento opcional de la cédula de identidad.
    complemento = forms.CharField(
        required=False,
        max_length=2,
        label="Complemento (Opcional)"
    )

    class Meta:
        """
        Configuración del formulario con base en el modelo User.
        """

        model = User

        fields = (
            "first_name",
            "last_name",
            "cedula_identidad",
            "complemento",
            "expedido",
            "celular",
            "rol",
            "email",
        )

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y personaliza visualmente sus campos.

        Si el formulario se usa para editar un usuario existente, se bloquean
        los campos relacionados con la cédula de identidad para evitar cambios
        en datos sensibles.
        """

        super().__init__(*args, **kwargs)

        # Aplica la clase Bootstrap 'form-control' a todos los campos.
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        # Si el usuario ya existe, se bloquean campos sensibles.
        if self.instance and self.instance.pk:
            campos_bloqueados = [
                "cedula_identidad",
                "complemento",
                "expedido",
            ]

            for campo in campos_bloqueados:
                self.fields[campo].disabled = True

                # Estilo visual para mostrar que el campo no se puede editar.
                self.fields[campo].widget.attrs.update({
                    "style": (
                        "background-color: #e2e8f0; "
                        "color: #64748b; "
                        "cursor: not-allowed; "
                        "opacity: 1;"
                    )
                })

    def clean_first_name(self):
        """
        Valida y normaliza el nombre del usuario.

        Elimina caracteres no permitidos y devuelve el texto en formato título.
        Ejemplo:
        'juan carlos' -> 'Juan Carlos'
        """

        nombre = self.cleaned_data.get("first_name")

        # Elimina números, símbolos y caracteres especiales no permitidos.
        nombre = re.sub(
            r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]",
            "",
            nombre
        )

        return nombre.title().strip()

    def clean_last_name(self):
        """
        Valida y normaliza el apellido del usuario.

        Elimina caracteres no permitidos y devuelve el texto en formato título.
        """

        apellido = self.cleaned_data.get("last_name")

        # Elimina números, símbolos y caracteres especiales no permitidos.
        apellido = re.sub(
            r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]",
            "",
            apellido
        )

        return apellido.title().strip()

    def clean_cedula_identidad(self):
        """
        Valida la cédula de identidad.

        Reglas:
        - Debe contener solo números.
        - Debe tener entre 5 y 10 dígitos.
        """

        ci = self.cleaned_data.get("cedula_identidad")

        if not ci.isdigit():
            raise ValidationError("El C.I. debe contener solo números.")

        if not (5 <= len(ci) <= 10):
            raise ValidationError("El C.I. debe tener entre 5 y 10 dígitos.")

        return ci

    def clean_complemento(self):
        """
        Valida el complemento de la cédula de identidad.

        El complemento es opcional, pero si se ingresa debe ser alfanumérico.
        """

        comp = self.cleaned_data.get("complemento")

        if comp and not comp.isalnum():
            raise ValidationError("El complemento debe ser alfanumérico.")

        # Se devuelve en mayúsculas para mantener uniformidad en la base de datos.
        return comp.upper() if comp else ""

    def clean_celular(self):
        """
        Valida el número de celular.

        Reglas:
        - Debe contener solo números.
        - Debe tener exactamente 8 dígitos.
        """

        cel = self.cleaned_data.get("celular")

        if not cel.isdigit():
            raise ValidationError("El celular debe contener solo números.")

        if len(cel) != 8:
            raise ValidationError("El celular debe tener exactamente 8 dígitos.")

        return cel

    def clean_rol(self):
        """
        Valida el rol del usuario.

        Regla de negocio:
        Solo puede existir un usuario activo con rol de director.
        """

        rol = self.cleaned_data.get("rol")

        if rol == "director":
            existe_director = (
                User.objects
                .filter(rol="director", is_active=True)
                .exclude(pk=self.instance.pk)
                .exists()
            )

            if existe_director:
                raise ValidationError(
                    "Ya existe un Director activo en el sistema. "
                    "Solo puede haber uno."
                )

        return rol


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Formulario personalizado para cambio de contraseña.

    Hereda de PasswordChangeForm de Django y aplica estilos CSS
    a todos sus campos.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y aplica la clase 'form-control'
        a cada campo.
        """

        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class SecureAuthenticationForm(AuthenticationForm):
    """
    Formulario seguro de autenticación.

    Además de validar usuario y contraseña, controla los intentos fallidos
    de inicio de sesión mediante el modelo LoginAttempt.

    Reglas principales:
    - Bloqueo temporal por intentos fallidos.
    - Bloqueo definitivo si se supera el límite permitido.
    - Desactivación automática de cuenta al llegar a 12 intentos fallidos.
    - Limpieza de intentos fallidos cuando el login es exitoso.
    """

    def clean(self):
        """
        Valida el inicio de sesión del usuario.

        Flujo:
        1. Obtiene username y password.
        2. Verifica si existe bloqueo temporal o permanente.
        3. Intenta autenticar al usuario.
        4. Registra intentos fallidos si la autenticación falla.
        5. Desactiva la cuenta si alcanza demasiados intentos.
        6. Limpia los intentos fallidos si el login es correcto.
        """

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        # Primero se valida el usuario, incluso antes de revisar la contraseña.
        if username:
            attempt, created = LoginAttempt.objects.get_or_create(
                username=username
            )

            # Bloqueo definitivo por demasiados intentos acumulados.
            if attempt.disabled_by_attempts:
                raise forms.ValidationError(
                    "La cuenta fue bloqueada por demasiados intentos fallidos. "
                    "Contacte al director o administrador."
                )

            # Bloqueo temporal. El usuario debe esperar antes de intentar otra vez.
            if attempt.is_locked():
                seconds = attempt.remaining_lock_seconds()
                minutes = max(1, seconds // 60)

                raise forms.ValidationError(
                    f"Demasiados intentos fallidos. "
                    f"Intente nuevamente en {minutes} minuto(s)."
                )

        # Si existen usuario y contraseña, se intenta autenticar.
        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )

            # Si la autenticación falla, se registra el intento fallido.
            if self.user_cache is None:
                attempt, created = LoginAttempt.objects.get_or_create(
                    username=username
                )

                attempt.register_failed_attempt()

                # Si alcanza 12 intentos, se desactiva la cuenta del usuario.
                if attempt.failed_attempts >= 12:
                    try:
                        user = User.objects.get(username=username)
                        user.is_active = False
                        user.save(update_fields=["is_active"])

                    except User.DoesNotExist:
                        # Si el usuario no existe, no se realiza ninguna acción adicional.
                        pass

                raise forms.ValidationError(
                    "Usuario o contraseña incorrectos."
                )

            # Si el usuario existe pero está desactivado, no se permite el ingreso.
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    "Esta cuenta está desactivada. Contacte al administrador."
                )

            # Si el inicio de sesión fue correcto, se eliminan los intentos fallidos.
            LoginAttempt.objects.filter(username=username).delete()

        return self.cleaned_data
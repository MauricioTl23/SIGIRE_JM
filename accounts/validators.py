import re

from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    """
    Validador personalizado de contraseñas seguras.

    Esta clase se puede registrar en la configuración AUTH_PASSWORD_VALIDATORS
    de Django para exigir que las contraseñas cumplan ciertos requisitos mínimos
    de seguridad.

    Reglas aplicadas:
    - Al menos una letra mayúscula.
    - Al menos una letra minúscula.
    - Al menos un número.
    - Al menos un símbolo.
    """

    def validate(self, password, user=None):
        """
        Valida que la contraseña cumpla con las reglas de seguridad definidas.

        Parámetros:
        - password: contraseña ingresada por el usuario.
        - user: usuario asociado a la contraseña. Es opcional y Django lo envía
          automáticamente cuando corresponde.

        Excepciones:
        - ValidationError: se lanza cuando la contraseña no cumple alguna regla.
        """

        # Verifica que la contraseña tenga al menos una letra mayúscula.
        # También considera vocales acentuadas y la letra Ñ.
        if not re.search(r"[A-ZÁÉÍÓÚÑ]", password):
            raise ValidationError(
                "La contraseña debe contener al menos una letra mayúscula.",
                code="password_no_uppercase",
            )

        # Verifica que la contraseña tenga al menos una letra minúscula.
        # También considera vocales acentuadas y la letra ñ.
        if not re.search(r"[a-záéíóúñ]", password):
            raise ValidationError(
                "La contraseña debe contener al menos una letra minúscula.",
                code="password_no_lowercase",
            )

        # Verifica que la contraseña tenga al menos un número.
        if not re.search(r"\d", password):
            raise ValidationError(
                "La contraseña debe contener al menos un número.",
                code="password_no_number",
            )

        # Verifica que la contraseña tenga al menos un símbolo.
        # Se considera símbolo cualquier carácter que no sea letra ni número.
        if not re.search(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ0-9]", password):
            raise ValidationError(
                "La contraseña debe contener al menos un símbolo.",
                code="password_no_symbol",
            )

    def get_help_text(self):
        """
        Devuelve el texto de ayuda que se muestra al usuario.

        Este mensaje informa cuáles son los requisitos mínimos que debe cumplir
        la contraseña.
        """

        return (
            "Tu contraseña debe incluir al menos una mayúscula, una minúscula, "
            "un número y un símbolo."
        )
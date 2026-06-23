from django.conf import settings
from django.db import models

from academic.models import Gestion, Paralelo
from students.models import Estudiante


# ============================================================
# MODELO INSCRIPCIÓN
# ============================================================

class Inscripcion(models.Model):
    """
    Modelo que representa la inscripción de un estudiante en una gestión escolar.

    Una inscripción relaciona:
    - Un estudiante.
    - Un paralelo.
    - Una gestión académica.
    - El usuario administrativo que realizó el registro.

    También controla el estado documental del estudiante, el RUDE,
    observaciones y si la inscripción sigue activa o fue cerrada.
    """

    # Opciones disponibles para el estado documental de la inscripción.
    ESTADO_DOCUMENTAL_CHOICES = [
        ("completa", "Completa"),
        ("pendiente", "Pendiente"),
        ("vencida", "Vencida"),
    ]

    # Estudiante inscrito.
    # Si se elimina el estudiante, también se eliminan sus inscripciones.
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE
    )

    # Paralelo al que será inscrito el estudiante.
    # Ejemplo: Primero de Primaria - Paralelo A.
    paralelo = models.ForeignKey(
        Paralelo,
        on_delete=models.CASCADE
    )

    # Usuario administrativo que realizó la inscripción.
    # Usa el modelo de usuario configurado en AUTH_USER_MODEL.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # Gestión escolar a la que pertenece la inscripción.
    # Ejemplo: 2025, 2026, etc.
    gestion = models.ForeignKey(
        Gestion,
        on_delete=models.CASCADE
    )

    # Fecha en la que se registró la inscripción.
    # Se llena automáticamente al crear el registro.
    fecha_registro = models.DateField(
        auto_now_add=True
    )

    # Estado lógico de la inscripción.
    # True significa activa, False significa cerrada o inactiva.
    estado = models.BooleanField(
        default=True
    )

    # Estado de los documentos requeridos para la inscripción.
    estado_documental = models.CharField(
        max_length=20,
        choices=ESTADO_DOCUMENTAL_CHOICES,
        default="pendiente"
    )

    # Fecha límite para entregar documentos pendientes.
    # Puede quedar vacía si no aplica.
    fecha_limite_documentos = models.DateField(
        null=True,
        blank=True
    )

    # Código RUDE del estudiante.
    # Es un identificador educativo importante dentro del contexto escolar.
    rude = models.CharField(
        max_length=100
    )

    # Observaciones adicionales sobre la inscripción.
    # Es opcional.
    observacion = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        """
        Devuelve una representación legible de la inscripción.

        Ejemplo:
        Juan Pérez - 2026
        """

        return f"{self.estudiante} - {self.gestion}"

    class Meta:
        """
        Configuración adicional del modelo Inscripcion.

        La restricción evita que un estudiante tenga más de una inscripción
        en la misma gestión escolar.

        El ordenamiento muestra primero las inscripciones más recientes.
        """

        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

        ordering = [
            "-gestion__anio",
            "estudiante__apellido_paterno",
            "estudiante__apellido_materno",
            "estudiante__nombres",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "estudiante",
                    "gestion",
                ],
                name="unique_estudiante_por_gestion"
            )
        ]


# ============================================================
# MODELO REQUISITO
# ============================================================

class Requisito(models.Model):
    """
    Modelo que representa un documento o requisito necesario para la inscripción.

    Ejemplos:
    - Certificado de nacimiento.
    - Fotocopia de C.I.
    - Libreta escolar.
    - Carnet de vacunas.

    Cada requisito puede ser obligatorio u opcional.
    """

    # Nombre del documento solicitado.
    nombre_documento = models.CharField(
        max_length=100
    )

    # Indica si el documento es obligatorio.
    obligatorio = models.BooleanField(
        default=True
    )

    # Estado lógico del requisito.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    def __str__(self):
        """
        Devuelve el nombre del documento como representación del requisito.
        """

        return self.nombre_documento

    class Meta:
        """
        Configuración adicional del modelo Requisito.
        """

        verbose_name = "Requisito"
        verbose_name_plural = "Requisitos"

        ordering = [
            "nombre_documento",
        ]


# ============================================================
# MODELO ENTREGA DE DOCUMENTO
# ============================================================

class EntregaDocumento(models.Model):
    """
    Modelo que registra la entrega de documentos de una inscripción.

    Este modelo permite controlar qué requisitos fueron entregados
    por el estudiante y cuáles siguen pendientes.

    Relaciona:
    - Una inscripción.
    - Un requisito.
    - El estado de entrega.
    - La fecha de entrega.
    - Una observación opcional.
    """

    # Inscripción a la que pertenece la entrega documental.
    inscripcion = models.ForeignKey(
        Inscripcion,
        on_delete=models.CASCADE
    )

    # Requisito o documento que debe entregarse.
    requisito = models.ForeignKey(
        Requisito,
        on_delete=models.CASCADE
    )

    # Estado de entrega del documento.
    # False significa pendiente, True significa entregado.
    estado = models.BooleanField(
        default=False
    )

    # Fecha en la que se entregó el documento.
    # Puede quedar vacía si todavía no fue entregado.
    fecha_entrega = models.DateField(
        null=True,
        blank=True
    )

    # Observación específica sobre este documento.
    # Ejemplo: "Falta firma", "Documento ilegible", etc.
    observacion = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        """
        Devuelve una representación legible de la entrega documental.

        Ejemplo:
        Juan Pérez - 2026 - Certificado de nacimiento
        """

        return f"{self.inscripcion} - {self.requisito}"

    class Meta:
        """
        Configuración adicional del modelo EntregaDocumento.

        La restricción evita registrar dos veces el mismo requisito
        dentro de una misma inscripción.
        """

        verbose_name = "Entrega de documento"
        verbose_name_plural = "Entregas de documentos"

        ordering = [
            "inscripcion",
            "requisito",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "inscripcion",
                    "requisito",
                ],
                name="unique_requisito_por_inscripcion"
            )
        ]
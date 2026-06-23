from django.core.exceptions import ValidationError
from django.db import models


# ============================================================
# MODELO NIVEL
# ============================================================

class Nivel(models.Model):
    """
    Modelo que representa un nivel académico dentro de la institución.

    Ejemplos:
    - Inicial
    - Primaria
    - Secundaria

    Campos:
    - nombre: nombre del nivel académico.
    - estado: indica si el nivel está activo o inactivo.
    """

    # Nombre del nivel académico.
    nombre = models.CharField(
        max_length=50
    )

    # Estado lógico del nivel.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    def __str__(self):
        """
        Devuelve el nombre del nivel como representación del objeto.

        Esto permite que en el panel de administración o en formularios
        se muestre el nombre del nivel en lugar de un texto genérico.
        """

        return self.nombre


# ============================================================
# MODELO GRADO
# ============================================================

class Grado(models.Model):
    """
    Modelo que representa un grado académico dentro de un nivel.

    Ejemplos:
    - Primero de Primaria
    - Segundo de Primaria
    - Primero de Secundaria

    Cada grado pertenece a un nivel académico.
    """

    # Opciones permitidas para el nombre del grado.
    NOMBRES_GRADOS = [
        ("Primero", "Primero"),
        ("Segundo", "Segundo"),
        ("Tercero", "Tercero"),
        ("Cuarto", "Cuarto"),
        ("Quinto", "Quinto"),
        ("Sexto", "Sexto"),
    ]

    # Nivel académico al que pertenece el grado.
    # related_name='grados' permite acceder desde un nivel a sus grados:
    # nivel.grados.all()
    nivel = models.ForeignKey(
        Nivel,
        on_delete=models.CASCADE,
        related_name="grados"
    )

    # Nombre del grado.
    # Se limita a las opciones definidas en NOMBRES_GRADOS.
    nombre = models.CharField(
        max_length=50,
        choices=NOMBRES_GRADOS
    )

    # Estado lógico del grado.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    @property
    def tiene_paralelos_activos(self):
        """
        Verifica si el grado tiene paralelos activos.

        Retorna:
        - True si existe al menos un paralelo activo asociado al grado.
        - False si no tiene paralelos activos.

        Uso:
        Esta propiedad puede servir para evitar eliminar o desactivar grados
        que todavía tienen paralelos en funcionamiento.
        """

        return self.paralelo_set.filter(estado=True).exists()

    def clean(self):
        """
        Valida reglas de negocio antes de guardar el grado.

        Reglas:
        1. Un nivel no puede tener más de 6 grados activos.
        2. No se puede repetir el mismo grado activo dentro del mismo nivel.

        Estas validaciones ayudan a mantener una estructura académica ordenada.
        """

        # Solo valida si existe un nivel y un nombre de grado seleccionado.
        if self.nivel_id and self.nombre:

            # Si el grado es nuevo, se valida que el nivel no tenga ya 6 grados activos.
            if not self.pk:
                if Grado.objects.filter(
                    nivel=self.nivel,
                    estado=True
                ).count() >= 6:
                    raise ValidationError(
                        f"El nivel '{self.nivel.nombre}' ya completó "
                        f"los 6 grados activos permitidos."
                    )

            # Si el grado es nuevo, se valida que no exista el mismo grado activo en el nivel.
            if not self.pk and Grado.objects.filter(
                nivel=self.nivel,
                nombre=self.nombre,
                estado=True
            ).exists():
                raise ValidationError(
                    f"El grado '{self.nombre}' ya existe y está activo en este nivel."
                )

    def save(self, *args, **kwargs):
        """
        Guarda el grado después de ejecutar sus validaciones.

        full_clean() llama internamente al método clean().
        Esto asegura que las reglas de negocio también se apliquen
        aunque el objeto se guarde desde código y no solo desde formularios.
        """

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Devuelve una representación legible del grado.
        """

        return f"{self.nombre} - {self.nivel.nombre}"


# ============================================================
# MODELO GESTIÓN
# ============================================================

class Gestion(models.Model):
    """
    Modelo que representa una gestión escolar o año académico.

    Ejemplos:
    - 2024
    - 2025
    - 2026

    Campos:
    - anio: año de la gestión escolar.
    - estado: indica si la gestión está activa o inactiva.
    """

    # Año escolar de la gestión.
    anio = models.IntegerField()

    # Estado lógico de la gestión.
    # True significa activa, False significa inactiva.
    estado = models.BooleanField(
        default=True
    )

    def __str__(self):
        """
        Devuelve el año de la gestión como texto.

        Esto permite mostrar la gestión de forma clara en formularios,
        reportes y panel administrativo.
        """

        return str(self.anio)


# ============================================================
# MODELO PARALELO
# ============================================================

class Paralelo(models.Model):
    """
    Modelo que representa un paralelo dentro de un grado.

    Ejemplos:
    - Primero de Primaria - Paralelo A
    - Segundo de Secundaria - Paralelo B

    Cada paralelo pertenece a un grado académico.
    """

    # Grado al que pertenece el paralelo.
    # related_name='paralelos' permite acceder desde un grado a sus paralelos:
    # grado.paralelos.all()
    grado = models.ForeignKey(
        Grado,
        on_delete=models.CASCADE,
        related_name="paralelos"
    )

    # Letra o identificador del paralelo.
    # Ejemplos: A, B, C.
    letra = models.CharField(
        max_length=2
    )

    # Cupo máximo permitido para el paralelo.
    # Por defecto, cada paralelo admite 30 estudiantes.
    cupo_max = models.PositiveIntegerField(
        default=30
    )

    # Estado lógico del paralelo.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    @property
    def tiene_inscritos(self):
        """
        Verifica si el paralelo tiene inscripciones asociadas.

        Retorna:
        - True si existe al menos una inscripción relacionada.
        - False si no tiene inscripciones.

        Uso:
        Esta propiedad puede servir para evitar eliminar paralelos
        que ya tienen estudiantes inscritos.
        """

        return self.inscripcion_set.exists()

    class Meta:
        """
        Configuración adicional del modelo Paralelo.

        Restricciones:
        - No puede existir el mismo paralelo repetido dentro del mismo grado.

        Ordenamiento:
        - Los paralelos se ordenan por grado y letra.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["grado", "letra"],
                name="unique_paralelo_por_grado",
                violation_error_message=(
                    "Este paralelo ya existe para el grado seleccionado."
                ),
            )
        ]

        ordering = [
            "grado",
            "letra",
        ]

    def __str__(self):
        """
        Devuelve una representación legible del paralelo.

        Ejemplo:
        Primero (Primaria) - Paralelo A
        """

        return (
            f"{self.grado.nombre} "
            f"({self.grado.nivel.nombre}) - "
            f"Paralelo {self.letra}"
        )
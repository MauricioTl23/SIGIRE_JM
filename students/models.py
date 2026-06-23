from django.db import models


# ============================================================
# MODELO ESTUDIANTE
# ============================================================

class Estudiante(models.Model):
    """
    Modelo que representa a un estudiante registrado en el sistema.

    Este modelo almacena la información personal básica del estudiante,
    incluyendo nombres, apellidos, fecha de nacimiento, género, cédula
    de identidad, dirección, correo electrónico y estado.

    La cédula de identidad se usa como clave primaria, por lo tanto
    identifica de forma única a cada estudiante dentro de la base de datos.
    """

    # Opciones válidas para el género del estudiante.
    GENERO = (
        ("M", "Masculino"),
        ("F", "Femenino"),
    )

    # Nombres del estudiante.
    nombres = models.CharField(
        max_length=100
    )

    # Apellido paterno del estudiante.
    apellido_paterno = models.CharField(
        max_length=100
    )

    # Apellido materno del estudiante.
    apellido_materno = models.CharField(
        max_length=100
    )

    # Fecha de nacimiento del estudiante.
    # Este campo se usa también para validar la edad mínima de inscripción.
    fecha_nacimiento = models.DateField()

    # Género del estudiante.
    genero = models.CharField(
        max_length=1,
        choices=GENERO
    )

    # Cédula de identidad del estudiante.
    # Se usa como clave primaria y debe ser única.
    cedula_identidad = models.CharField(
        max_length=20,
        unique=True,
        primary_key=True
    )

    # Dirección del estudiante.
    # En el formulario se construye usando zona, avenida y número de puerta.
    direccion = models.CharField(
        max_length=200
    )

    # Correo electrónico del estudiante.
    # Es opcional porque no todos los estudiantes pueden tener correo propio.
    correo_electronico = models.EmailField(
        blank=True,
        null=True
    )

    # Estado lógico del estudiante.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    def __str__(self):
        """
        Devuelve una representación legible del estudiante.

        Esto permite mostrar el nombre del estudiante en el panel de administración,
        formularios, relaciones y consultas.
        """

        return f"{self.nombres} {self.apellido_paterno}"

    class Meta:
        """
        Configuración adicional del modelo Estudiante.
        """

        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = [
            "apellido_paterno",
            "apellido_materno",
            "nombres",
        ]


# ============================================================
# MODELO TUTOR
# ============================================================

class Tutor(models.Model):
    """
    Modelo que representa a un tutor o responsable de un estudiante.

    Este modelo almacena datos personales del tutor, como nombres, apellidos,
    cédula de identidad, ocupación, celular y estado.

    La relación entre tutor y estudiante no se guarda directamente aquí,
    sino mediante el modelo Parentesco.
    """

    # Nombres del tutor.
    nombres = models.CharField(
        max_length=100
    )

    # Apellidos del tutor.
    apellidos = models.CharField(
        max_length=100
    )

    # Cédula de identidad del tutor.
    # Se usa como clave primaria para identificarlo de forma única.
    cedula_identidad = models.CharField(
        max_length=20,
        primary_key=True
    )

    # Ocupación del tutor.
    ocupacion = models.CharField(
        max_length=100
    )

    # Número de celular del tutor.
    celular = models.CharField(
        max_length=20
    )

    # Estado lógico del tutor.
    # True significa activo, False significa inactivo.
    estado = models.BooleanField(
        default=True
    )

    # Fecha en la que el tutor fue dado de baja.
    # Es opcional y solo se llena cuando corresponde.
    fecha_baja = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        """
        Devuelve una representación legible del tutor.
        """

        return f"{self.nombres} {self.apellidos}"

    @property
    def tiene_estudiantes(self):
        """
        Verifica si el tutor tiene estudiantes asociados.

        Retorna:
        - True si existe al menos una relación de parentesco.
        - False si el tutor no está relacionado con ningún estudiante.

        Uso:
        Puede servir para evitar eliminar o desactivar tutores
        que todavía tienen estudiantes asociados.
        """

        return self.parentesco_set.exists()

    class Meta:
        """
        Configuración adicional del modelo Tutor.
        """

        verbose_name = "Tutor"
        verbose_name_plural = "Tutores"
        ordering = [
            "apellidos",
            "nombres",
        ]


# ============================================================
# MODELO PARENTESCO
# ============================================================

class Parentesco(models.Model):
    """
    Modelo que representa la relación entre un estudiante y un tutor.

    Este modelo permite vincular estudiantes con sus respectivos tutores
    indicando el tipo de relación familiar o de responsabilidad.

    Ejemplos de relación:
    - Padre
    - Madre
    - Tutor legal
    - Abuelo
    - Hermano
    """

    # Estudiante asociado al parentesco.
    # Si se elimina el estudiante, también se eliminan sus relaciones.
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE
    )

    # Tutor asociado al parentesco.
    # Si se elimina el tutor, también se eliminan sus relaciones.
    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE
    )

    # Tipo de relación entre el tutor y el estudiante.
    relacion = models.CharField(
        max_length=50
    )

    def __str__(self):
        """
        Devuelve una representación legible del parentesco.

        Ejemplo:
        Juan Pérez - Padre
        """

        return f"{self.estudiante} - {self.relacion}"

    class Meta:
        """
        Configuración adicional del modelo Parentesco.

        La restricción evita que se registre dos veces el mismo tutor
        para el mismo estudiante con la misma relación.
        """

        verbose_name = "Parentesco"
        verbose_name_plural = "Parentescos"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "estudiante",
                    "tutor",
                    "relacion",
                ],
                name="unique_parentesco_estudiante_tutor_relacion"
            )
        ]
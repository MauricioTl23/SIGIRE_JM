from django.db import models

# Clases para el manejo de estudiantes,tutores y parentesco 

#CLASE ESTUDIANTE
class Estudiante(models.Model):
    
    GENERO = (
        ("M", "Masculino"),
        ("F", "Femenino"),
    )
    
    nombres = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100)

    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=1, choices=GENERO)

    cedula_identidad = models.CharField(max_length=20, unique=True, primary_key=True)

    direccion = models.CharField(max_length=200)
    correo_electronico = models.EmailField(blank=True, null=True)

    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombres} {self.apellido_paterno}"

#CLASE TUTOR
class Tutor(models.Model):

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    cedula_identidad = models.CharField(max_length=20,primary_key=True)

    ocupacion = models.CharField(max_length=100)
    celular = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

#CLASE PARENTESCO
class Parentesco(models.Model):

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE
    )

    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE
    )

    relacion = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.estudiante} - {self.relacion}"

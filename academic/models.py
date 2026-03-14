from django.db import models

# Clases para el manejo de Nivel, Grado, Gestion y Paralelo

#CLASE NIVEL
class Nivel(models.Model):

    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

#CLASE GRADO
class Grado(models.Model):

    nivel = models.ForeignKey(
        Nivel,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

#CLASE GESTION
class Gestion(models.Model):

    año = models.IntegerField()
    estado = models.BooleanField(default=True)

    def __str__(self):
        return str(self.año)

#CLASE PARALELO
class Paralelo(models.Model):

    grado = models.ForeignKey(
        Grado,
        on_delete=models.CASCADE
    )

    letra = models.CharField(max_length=2)
    cupo_max = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.grado} {self.letra}"

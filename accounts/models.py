from django.db import models

# Clase para el manejo de usuarios
from django.contrib.auth.models import AbstractUser
from django.db import models   

class User(AbstractUser):
    
    class Roles(models.TextChoices):
        DIRECTOR = "director", "Director(a)"
        SECRETARIA = "secretaria", "Secretaría"
    
    cedula_identidad = models.CharField(max_length=20, unique=True, primary_key=True)
    celular = models.CharField(max_length=20)

    rol = models.CharField(
        max_length=15,
        choices=Roles.choices,
        default=Roles.SECRETARIA
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
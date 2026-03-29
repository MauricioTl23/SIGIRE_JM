from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    class Roles(models.TextChoices):
        DIRECTOR = "director", "Director(a)"
        SECRETARIA = "secretaria", "Secretaría"

    # Opciones para el campo expedido (Bolivia)
    DEPARTAMENTOS_CHOICES = [
        ('LP', 'La Paz'), ('OR', 'Oruro'), ('PT', 'Potosí'),
        ('CB', 'Cochabamba'), ('SC', 'Santa Cruz'), ('BN', 'Beni'),
        ('PA', 'Pando'), ('TJ', 'Tarija'), ('CH', 'Chuquisaca'),
    ]
    
    # Campos de Identidad
    cedula_identidad = models.CharField(max_length=20, unique=True, primary_key=True)
    complemento = models.CharField(max_length=2, blank=True, null=True)
    expedido = models.CharField(
        max_length=2, 
        choices=DEPARTAMENTOS_CHOICES, 
        blank=True, 
        null=True
    )
    
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'cedula_identidad']

    # Contacto y Rol
    celular = models.CharField(max_length=20)
    rol = models.CharField(
        max_length=15,
        choices=Roles.choices,
        default=Roles.SECRETARIA
    )

    def __str__(self):
        # Usamos self.get_full_name() que ya viene en AbstractUser o el personalizado
        nombre_completo = f"{self.first_name} {self.last_name}".strip()
        return nombre_completo if nombre_completo else self.username

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
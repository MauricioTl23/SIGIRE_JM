from django.contrib import admin
from .models import Nivel, Grado, Paralelo, Gestion

# Register your models here.
admin.site.register(Nivel)
admin.site.register(Grado)
admin.site.register(Paralelo)
admin.site.register(Gestion)
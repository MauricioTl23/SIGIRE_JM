from django.contrib import admin
from .models import Inscripcion, Requisito, EntregaDocumento

# Register your models here.
admin.site.register(Inscripcion)
admin.site.register(Requisito)
admin.site.register(EntregaDocumento)
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm
from .models import User
from django.core.exceptions import ValidationError
import re

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    
class RegistroPersonalForm(forms.ModelForm):
    
    DEPARTAMENTOS_CHOICES = [
        ('LP', 'La Paz'), ('OR', 'Oruro'), ('PT', 'Potosí'),
        ('CB', 'Cochabamba'), ('SC', 'Santa Cruz'), ('BN', 'Beni'),
        ('PA', 'Pando'), ('TJ', 'Tarija'), ('CH', 'Chuquisaca'),
    ]

    email = forms.EmailField(required=True, label="Correo Electrónico")
    
    expedido = forms.ChoiceField(choices=DEPARTAMENTOS_CHOICES, label="Expedido en")
    complemento = forms.CharField(required=False, max_length=2, label="Complemento (Opcional)")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "cedula_identidad", "complemento", "expedido", "celular", "rol", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_first_name(self):
        nombre = self.cleaned_data.get('first_name')
        nombre = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', nombre)
        return nombre.title().strip()

    def clean_last_name(self):
        apellido = self.cleaned_data.get('last_name')
        apellido = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', apellido)
        return apellido.title().strip()

    def clean_cedula_identidad(self):
        ci = self.cleaned_data.get('cedula_identidad')
        if not ci.isdigit():
            raise ValidationError("El C.I. debe contener solo números.")
        if not (5 <= len(ci) <= 10):
            raise ValidationError("El C.I. debe tener entre 5 y 10 dígitos.")
        return ci

    def clean_complemento(self):
        comp = self.cleaned_data.get('complemento')
        if comp and not comp.isalnum():
            raise ValidationError("El complemento debe ser alfanumérico.")
        return comp.upper() if comp else ""

    def clean_celular(self):
        cel = self.cleaned_data.get('celular')
        if not cel.isdigit():
            raise ValidationError("El celular debe contener solo números.")
        if len(cel) != 8:
            raise ValidationError("El celular debe tener exactamente 8 dígitos.")
        return cel
    
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
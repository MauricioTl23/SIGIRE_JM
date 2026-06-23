from django import forms
from django.utils import timezone

from .models import Gestion, Nivel, Grado, Paralelo


# ============================================================
# FORMULARIO DE GESTIÓN ESCOLAR
# ============================================================

class GestionForm(forms.ModelForm):
    """
    Formulario para registrar una nueva gestión escolar.

    Este formulario permite ingresar el año académico de una gestión,
    por ejemplo: 2026, 2027, etc.

    Reglas principales:
    - No permite registrar años pasados.
    - No permite registrar una gestión que ya existe.
    """

    class Meta:
        """
        Configuración del formulario basado en el modelo Gestion.
        """

        model = Gestion
        fields = ["anio"]

        labels = {
            "anio": "Año Escolar (Ej. 2026)",
        }

        widgets = {
            "anio": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Ej. 2026",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario.

        Se asigna como año mínimo el año actual del sistema para evitar
        que el usuario seleccione una gestión pasada desde el campo HTML.
        """

        super().__init__(*args, **kwargs)

        # Obtiene el año actual según la zona horaria configurada en Django.
        año_actual = timezone.now().year

        # Define el valor mínimo permitido en el input numérico.
        self.fields["anio"].widget.attrs["min"] = año_actual

    def clean_anio(self):
        """
        Valida el año ingresado para la gestión escolar.

        Validaciones:
        - El año no puede ser menor al año actual.
        - El año no puede repetirse si ya existe una gestión registrada.

        Retorna:
        - El año validado.
        """

        año_ingresado = self.cleaned_data.get("anio")
        año_actual = timezone.now().year

        # Evita registrar gestiones con años pasados.
        if año_ingresado < año_actual:
            raise forms.ValidationError(
                f"No puedes registrar un año pasado. "
                f"El año mínimo es {año_actual}."
            )

        # Evita duplicar gestiones escolares.
        if Gestion.objects.filter(anio=año_ingresado).exists():
            raise forms.ValidationError(
                f"¡Atención! La gestión {año_ingresado} ya está registrada."
            )

        return año_ingresado


# ============================================================
# FORMULARIO DE NIVEL ACADÉMICO
# ============================================================

class NivelForm(forms.ModelForm):
    """
    Formulario para registrar o editar niveles académicos.

    Ejemplos de niveles:
    - Inicial
    - Primaria
    - Secundaria
    """

    class Meta:
        """
        Configuración del formulario basado en el modelo Nivel.
        """

        model = Nivel
        fields = ["nombre"]


# ============================================================
# FORMULARIO DE GRADO
# ============================================================

class GradoForm(forms.ModelForm):
    """
    Formulario para registrar o editar grados académicos.

    Permite asociar un grado a un nivel académico activo.

    Ejemplo:
    - Nivel: Primaria
    - Grado: Primero
    """

    # Opciones permitidas para el nombre del grado.
    OPCIONES_GRADOS = [
        ("Primero", "Primero"),
        ("Segundo", "Segundo"),
        ("Tercero", "Tercero"),
        ("Cuarto", "Cuarto"),
        ("Quinto", "Quinto"),
        ("Sexto", "Sexto"),
    ]

    # Campo select para elegir el grado.
    nombre = forms.ChoiceField(
        choices=OPCIONES_GRADOS,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    class Meta:
        """
        Configuración del formulario basado en el modelo Grado.
        """

        model = Grado
        fields = ["nivel", "nombre"]

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario.

        Se limita el campo nivel para mostrar únicamente niveles activos.
        Esto evita crear grados dentro de niveles desactivados.
        """

        super().__init__(*args, **kwargs)

        # Si el campo nivel existe, solo se muestran niveles activos.
        if "nivel" in self.fields:
            self.fields["nivel"].queryset = Nivel.objects.filter(estado=True)


# ============================================================
# FORMULARIO DE PARALELO
# ============================================================

class ParaleloForm(forms.ModelForm):
    """
    Formulario para registrar paralelos académicos.

    Permite seleccionar primero un nivel y luego un grado asociado.

    Ejemplo:
    - Nivel: Primaria
    - Grado: Primero
    - Paralelo: A

    Nota:
    Aunque el campo nivel no pertenece directamente al modelo Paralelo,
    se agrega al formulario para facilitar el filtrado visual de grados.
    """

    # Campo auxiliar para seleccionar el nivel académico.
    nivel = forms.ModelChoiceField(
        queryset=Nivel.objects.filter(estado=True),
        required=True,
        empty_label="-- Elige Nivel --",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "filtro_nivel",
                "onchange": "filtrarGrados()",
            }
        ),
    )

    class Meta:
        """
        Configuración del formulario basado en el modelo Paralelo.

        Solo se guarda el campo grado, porque el paralelo pertenece
        directamente a un grado.
        """

        model = Paralelo
        fields = ["grado"]

        widgets = {
            "grado": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "select_grado",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario de paralelo.

        Personaliza las opciones del campo grado para mostrar el nombre
        del grado junto con su nivel correspondiente.

        Ejemplo visible:
        - Primero - Primaria
        - Segundo - Primaria
        - Primero - Secundaria
        """

        super().__init__(*args, **kwargs)

        # Texto inicial mostrado en el select de grados.
        self.fields["grado"].empty_label = "-- Elige Grado --"

        # Se cargan únicamente grados activos junto con su nivel.
        self.fields["grado"].choices = [
            ("", "-- Elige Grado --")
        ] + [
            (
                g.id,
                f"{g.nombre} - {g.nivel.nombre}",
            )
            for g in Grado.objects.select_related("nivel").filter(estado=True)
        ]
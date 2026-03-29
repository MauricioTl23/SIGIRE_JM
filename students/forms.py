from django import forms
from .models import Tutor

class TutorForm(forms.ModelForm):
    ci_nro = forms.CharField(max_length=10, label="Número de CI")
    ci_comp = forms.CharField(max_length=2, required=False, label="Complemento")
    ci_exp = forms.ChoiceField(choices=[
        ('LP', 'La Paz'), ('OR', 'Oruro'), ('PT', 'Potosí'),
        ('CB', 'Cochabamba'), ('SC', 'Santa Cruz'), ('BN', 'Beni'),
        ('PA', 'Pando'), ('TJ', 'Tarija'), ('CH', 'Chuquisaca')
    ], label="Expedido")

    class Meta:
        model = Tutor
        fields = ['nombres', 'apellidos', 'celular', 'ocupacion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'tutor-input', 'placeholder': 'Escriba aquí...'})

    def save(self, commit=True):
        tutor = super().save(commit=False)
        
        nro = self.cleaned_data['ci_nro']
        comp = self.cleaned_data['ci_comp']
        exp = self.cleaned_data['ci_exp']
        
        if comp:
            tutor.cedula_identidad = f"{nro}-{comp} {exp}"
        else:
            tutor.cedula_identidad = f"{nro} {exp}"
            
        if commit:
            tutor.save()
        return tutor
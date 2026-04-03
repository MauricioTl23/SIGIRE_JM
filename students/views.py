from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tutor
from django.shortcuts import get_object_or_404
from .forms import TutorForm

@login_required
def registrar_tutor(request):
    if request.method == 'POST':
        form = TutorForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Tutor registrado correctamente.")
            return redirect('list_tutores')
        else:
            messages.error(request, "Error en el formulario. Verifique los datos.")

    else:
        form = TutorForm()
    
    return render(request, 'Tutor/form_tutor.html', {'form': form})
@login_required


def list_tutores(request):
    tutores = Tutor.objects.all().order_by('apellidos')
    return render(request, 'Tutor/list_tutores.html', {'tutores': tutores})


@login_required

def editar_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    if request.method == 'POST':
        form = TutorForm(request.POST, instance=tutor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de {tutor.nombres} {tutor.apellidos} actualizados.")
            return redirect('list_tutores')
    else:
        ci_parts = tutor.cedula_identidad.split('-')

        initial = {
            'ci_nro': ci_parts[0],
            'ci_comp': ci_parts[1] if len(ci_parts) == 3 else '',
            'ci_exp': ci_parts[-1],
        }

        form = TutorForm(instance=tutor, initial=initial)

    return render(request, 'Tutor/form_tutor.html', {
        'form': form,
        'edit_mode': True,
        'tutor': tutor
    })


@login_required
def eliminar_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    tutor.delete()

    messages.warning(request, f"El tutor {tutor.nombres} ha sido eliminado.")

    return redirect('list_tutores')
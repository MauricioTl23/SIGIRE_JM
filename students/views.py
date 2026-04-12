from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tutor, Estudiante
from .forms import TutorForm,EstudianteForm
from django.urls import reverse


@login_required
def registrar_tutor(request):
    if request.method == 'POST':
        form = TutorForm(request.POST)

        if form.is_valid():
            
            tutor = form.save() 
            messages.success(request, "Tutor registrado correctamente.")
            
            base_url = reverse('list_tutores')
            return redirect(f"{base_url}?nuevo_tutor_id={tutor.pk}")
            
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

# @login_required
# def crear_estudiante(request):
#     tutor_id = request.GET.get('tutor_id')
#     tutor_obj = None
#     mostrar_pregunta = False

#     if tutor_id:
#         try:
#             tutor_obj = Tutor.objects.get(pk=tutor_id)
#         except Tutor.DoesNotExist:
#             tutor_obj = None
#     else:
#         mostrar_pregunta = True

#     context = {
#         'tutor_seleccionado': tutor_obj,
#         'mostrar_pregunta': mostrar_pregunta,
#     }
#     return render(request, 'Student/form_student.html', context)

@login_required
def list_estudiantes(request):
    estudiantes = Estudiante.objects.all()
    return render(request, 'Student/list_estudiantes.html', {'estudiantes': estudiantes})

#REGISTRAR ESTUDIANTE 

@login_required
def crear_estudiante(request):
    tutor_id = request.GET.get('tutor_id')
    tutor_guardar = None
    mostrar_pregunta = False

    if tutor_id:
        try:
            tutor_guardar = Tutor.objects.get(pk=tutor_id)
        except Tutor.DoesNotExist:
            tutor_guardar = None
    else:
        mostrar_pregunta = True

    if request.method == "POST":
        form = EstudianteForm(request.POST)

        if form.is_valid():
            messages.success(request, "Estudiante registrado correctamente.")   
            form.save()
            return redirect("list_estudiantes")
        else:
            messages.error(request, "Error en el formulario. Verifique los datos.") 
    else:
        form = EstudianteForm()

    context = {
        'form': form,  
        'tutor_seleccionado': tutor_guardar,
        'mostrar_pregunta': mostrar_pregunta,
    }

    return render(request, 'Student/form_student.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tutor, Estudiante, Parentesco
from .forms import TutorForm,EstudianteForm, EditarEstudianteForm
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q


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
    query = request.GET.get('search', '')
    
    tutores = Tutor.objects.filter(estado=True).order_by('apellidos')
    
    if query:
        tutores = tutores.filter(
            Q(nombres__icontains=query) | 
            Q(apellidos__icontains=query) | 
            Q(cedula_identidad__icontains=query) |
            Q(ocupacion__icontains=query)
        ).distinct()
        
    return render(request, 'Tutor/list_tutores.html', {
        'tutores': tutores,
        'search_query': query
    })


@login_required
def editar_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    ci_parts = tutor.cedula_identidad.split('-')
    initial_data = {
        'ci_nro': ci_parts[0],
        'ci_comp': ci_parts[1] if len(ci_parts) == 3 else '',
        'ci_exp': ci_parts[-1],
    }

    if request.method == 'POST':
        form = TutorForm(request.POST, instance=tutor, initial=initial_data)
        
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, f"Datos de {tutor.nombres} {tutor.apellidos} actualizados correctamente.")
            else:
                messages.info(request, "No se detectaron modificaciones en el formulario.")
                
            return redirect('list_tutores')
            
        else:
        
            print("Errores del formulario:", form.errors)
            messages.error(request, "Error de validación. Revisa los datos ingresados.")
            
    else:
        form = TutorForm(instance=tutor, initial=initial_data)

    return render(request, 'Tutor/form_tutor.html', {
        'form': form,
        'edit_mode': True,
        'tutor': tutor
    })


@login_required
def eliminar_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    
 
    if tutor.tiene_estudiantes:
        messages.error(request, f"El tutor {tutor.nombres} {tutor.apellidos} no se puede eliminar porque tiene estudiantes asociados.")
        return redirect('list_tutores')
 
    tutor.estado = False
    tutor.fecha_baja = timezone.now() 
    tutor.save()
    
    messages.warning(request, f"El tutor {tutor.nombres} fue enviado a la papelera. Se eliminará definitivamente en 30 días.")
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

    query = request.GET.get('search', '').strip()
    genero_filtro = request.GET.get('genero', '')
    ver_inactivos = request.GET.get('inactivos') == 'on'

    estudiantes = Estudiante.objects.all().order_by('apellido_paterno')

    if ver_inactivos:
        estudiantes = estudiantes.filter(estado=False)
    else:
        estudiantes = estudiantes.filter(estado=True)

    if query:
        estudiantes = estudiantes.filter(
            Q(nombres__icontains=query) |
            Q(apellido_paterno__icontains=query) |
            Q(apellido_materno__icontains=query) |
            Q(cedula_identidad__icontains=query)
        ).distinct()

    if genero_filtro:
        estudiantes = estudiantes.filter(genero=genero_filtro)

    return render(request, 'Student/list_estudiantes.html', {
        'estudiantes': estudiantes,
        'search_query': query,
        'genero_filter': genero_filtro,
        'ver_inactivos': ver_inactivos
    })

#REGISTRAR ESTUDIANTE 
@login_required
def crear_estudiante(request):
    tutor_id = request.GET.get('tutor_id') or request.POST.get('tutor_id')
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

        if not tutor_guardar:
            messages.error(request, "Error de seguridad: Se requiere un tutor para registrar al estudiante.")
            return redirect("list_tutores")

        if form.is_valid():
            nuevo_estudiante = form.save()
            
            tipo_relacion = request.POST.get('relacion', 'Apoderado')

            Parentesco.objects.create(
                estudiante=nuevo_estudiante,
                tutor=tutor_guardar,
                relacion=tipo_relacion
            )

            messages.success(request, f"Estudiante {nuevo_estudiante.nombres} y Tutor vinculados correctamente.")   
            
           
            url_destino = reverse('list_estudiantes')
            return redirect(f"{url_destino}?registrado_id={nuevo_estudiante.pk}&nombre_est={nuevo_estudiante.nombres}")
           
            
        else:
            messages.error(request, "Error en el formulario. Verifique los datos.") 
    else:
        form = EstudianteForm()

    departamentos = form.fields['ci_exp'].choices if 'ci_exp' in form.fields else []

    context = {
        'form': form,  
        'tutor_seleccionado': tutor_guardar,
        'mostrar_pregunta': mostrar_pregunta,
        'departamentos': departamentos, 
    }

    return render(request, 'Student/form_student.html', context)

@login_required
def eliminar_estudiante_fisico(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)

    if estudiante.inscripcion_set.exists():
        messages.error(request, "Error de seguridad: El estudiante tiene inscripciones históricas.")
        return redirect('/estudiantes/?inactivos=on')

    relacion = estudiante.parentesco_set.first()
    if relacion:
        tutor = relacion.tutor
    
        otros_hijos = tutor.parentesco_set.exclude(estudiante=estudiante).count()

        if otros_hijos > 0:
            messages.error(request, "Error: No se puede eliminar. El tutor tiene otros estudiantes asociados.")
            return redirect('/estudiantes/?inactivos=on')
        else:
            tutor.delete()

    nombre = f"{estudiante.nombres} {estudiante.apellido_paterno}"
    estudiante.delete()
    
    messages.success(request, f"¡Completado! El estudiante {nombre} y su tutor han sido eliminados de la base de datos.")
    return redirect('/estudiantes/?inactivos=on')

@login_required
def desactivar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
   
    estudiante.estado = False
    estudiante.save()
    
    messages.warning(request, f"El estudiante {estudiante.nombres} ha sido desactivado.")
    return redirect('list_estudiantes')

@login_required
def reactivar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
 
    estudiante.estado = True
    estudiante.save()
    
    messages.success(request, f"El estudiante {estudiante.nombres} ha sido reactivado.")
    return redirect('/estudiantes/?inactivos=on')

@login_required
def editar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    
    full_ci = estudiante.cedula_identidad.strip().upper()
    
    full_ci_norm = full_ci.replace(' ', '-')
    
    while '--' in full_ci_norm:
        full_ci_norm = full_ci_norm.replace('--', '-')
        
    partes_ci = full_ci_norm.split('-')
    
    nro = partes_ci[0] if len(partes_ci) > 0 else ""
    comp = ""
    expedido = ""
    
    if len(partes_ci) == 3:
        comp = partes_ci[1]
        expedido = partes_ci[2]
    elif len(partes_ci) == 2:
        expedido = partes_ci[1] 
        
    dir_texto = estudiante.direccion
    calle = ""
    numero = ""
    zona = ""
    
    if ', ' in dir_texto:
        partes_dir = dir_texto.split(', ')
        zona = partes_dir[0] if len(partes_dir) > 0 else ""
        calle = partes_dir[1] if len(partes_dir) > 1 else ""
        if len(partes_dir) > 2:
            numero = partes_dir[2].replace("N° ", "").strip()
    else:
        calle = dir_texto 

    if request.method == "POST":
        form = EditarEstudianteForm(request.POST, instance=estudiante)
        
        if form.is_valid():
            est_modificado = form.save(commit=False)
            
            zona_post = form.cleaned_data.get('zona', '')
            calle_post = form.cleaned_data.get('avenida', '')
            nro_post = form.cleaned_data.get('num_puerta', '')
            
            est_modificado.direccion = f"{zona_post}, {calle_post}, N° {nro_post}"
            
            est_modificado.save()
            
            messages.success(request, f"Datos de {est_modificado.nombres} actualizados.")
            return redirect('list_estudiantes')
        else:
            print("\n--- ERRORES EN EDICIÓN ---")
            print(form.errors)
            print("--------------------------\n")
            messages.error(request, "Error en el formulario. Verifique los datos.")
    else:
        form = EditarEstudianteForm(instance=estudiante)

    DEPARTAMENTOS = [
        ('LP', 'La Paz'), ('OR', 'Oruro'), ('PT', 'Potosí'), 
        ('CB', 'Cochabamba'), ('SC', 'Santa Cruz'), ('BN', 'Beni'), 
        ('PA', 'Pando'), ('TJ', 'Tarija'), ('CH', 'Chuquisaca')
    ]

    return render(request, 'Student/form_student.html', {
        'form': form,
        'estudiante': estudiante,
        'es_edicion': True,
        'ci_nro_val': nro,
        'ci_comp_val': comp,
        'ci_exp_val': expedido,
        'dir_calle': calle,
        'dir_nro': numero,
        'dir_zona': zona,
        'departamentos': DEPARTAMENTOS 
    })
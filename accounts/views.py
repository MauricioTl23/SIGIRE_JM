import random
import string
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .email_api import enviar_correo_brevo
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .forms import RegistroPersonalForm
from .models import User
from .decorators import only_director, only_administrative
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .forms import CustomPasswordChangeForm
from django.db.models import Sum
from students.models import Estudiante
from enrollment.models import Inscripcion
from academic.models import Gestion, Paralelo, Nivel, Grado


# 1. Vista Pública
def home(request):
    return render(request, 'registration/home.html') 

# 4. Listado de Personal (RF1 - Solo Director)
@login_required
@only_director
def list_personal(request):

    mostrar_inactivos = request.GET.get('inactivos') == 'true'
    query_busqueda = request.GET.get('q', '').strip() 
    rol_filtro = request.GET.get('rol', '') 

    if mostrar_inactivos:
        personal = User.objects.filter(is_active=False)
    else:
        personal = User.objects.filter(is_active=True)
    
    if query_busqueda:
        personal = personal.filter(
            Q(cedula_identidad__icontains=query_busqueda) |
            Q(first_name__icontains=query_busqueda) |
            Q(last_name__icontains=query_busqueda) |
            Q(celular__icontains=query_busqueda)
        )

    if rol_filtro:
        personal = personal.filter(rol=rol_filtro)
    
    return render(request, 'registration/list_personal.html', {
        'personal': personal,
        'mostrar_inactivos': mostrar_inactivos,
        'query_busqueda': query_busqueda, 
        'rol_filtro': rol_filtro,
    })

# 5. Registro de Personal (RF1 - Solo Director)
@login_required
@only_director
def registrar_personal(request):
    if request.method == 'POST':
        form = RegistroPersonalForm(request.POST)
        if form.is_valid():
            nuevo_usuario = form.save(commit=False)

            nombre_raw = nuevo_usuario.first_name.split()[0] if nuevo_usuario.first_name else "User"
            nombre = nombre_raw.capitalize()

            apellidos = nuevo_usuario.last_name.split() if nuevo_usuario.last_name else ["X"]
            iniciales = "".join([a[0].upper() for a in apellidos])

            def generar_propuesta():
                digitos = "".join(random.choices(string.digits, k=3))
                return f"{nombre}{iniciales}{digitos}"

            username_final = generar_propuesta()

            while User.objects.filter(username=username_final).exists():
                username_final = generar_propuesta()

            nuevo_usuario.username = username_final

            password_temporal = get_random_string(length=10)
            nuevo_usuario.set_password(password_temporal)

            asunto = 'Bienvenido al Sistema - UE Jesús María'
            mensaje = (
                f"Hola {nuevo_usuario.first_name},\n\n"
                f"Tu cuenta administrativa ha sido creada.\n"
                f"Usuario: {username_final}\n"
                f"Contraseña temporal: {password_temporal}\n\n"
                f"Por seguridad, cambia tu contraseña al ingresar por primera vez."
            )

            try:
                enviar_correo_brevo(
                    destinatario_email=nuevo_usuario.email,
                    destinatario_nombre=nuevo_usuario.first_name,
                    asunto=asunto,
                    mensaje=mensaje,
                )

                nuevo_usuario.save()

                messages.success(
                    request,
                    f"Personal registrado. Credenciales enviadas a {nuevo_usuario.email}"
                )

                return redirect('list_personal')

            except Exception as e:
                print(f"DEBUG: Error al enviar correo: {e}")
                messages.error(
                    request,
                    f"No se registró el usuario porque no se pudo enviar el correo: {e}"
                )

    else:
        form = RegistroPersonalForm()

    return render(request, 'registration/form_personal.html', {'form': form})


@login_required
@only_director
def editar_personal(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        
        form = RegistroPersonalForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de {usuario.get_full_name()} actualizados.")
            return redirect('list_personal')
    else:
        form = RegistroPersonalForm(instance=usuario)
    return render(request, 'registration/form_personal.html', {
        'form': form, 
        'edit_mode': True,
        'usuario': usuario
    })

@login_required
@only_director
def eliminar_personal(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    # Evitar que el director se borre a sí mismo
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
    else:
        # Borrado lógico: lo desactivamos en lugar de borrarlo de la BD
        usuario.is_active = False
        usuario.save()
        messages.warning(request, f"El usuario {usuario.username} ha sido desactivado.")
    
    return redirect('list_personal')

class UserPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/change_password.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        messages.success(self.request, "¡Tu contraseña ha sido actualizada con éxito!")
        return super().form_valid(form)
    
@login_required
@only_director
def reactivar_personal(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    password_temporal = get_random_string(length=10)

    asunto = 'Reactivación de Cuenta - UE Jesús María'
    mensaje = (
        f"Hola {usuario.first_name},\n\n"
        f"Tu cuenta administrativa ha sido reactivada en el sistema.\n"
        f"Usuario: {usuario.username}\n"
        f"Nueva contraseña temporal: {password_temporal}\n\n"
        f"Por seguridad, te pedimos que cambies tu contraseña inmediatamente al ingresar."
    )

    try:
        enviar_correo_brevo(
            destinatario_email=usuario.email,
            destinatario_nombre=usuario.first_name,
            asunto=asunto,
            mensaje=mensaje,
        )

        usuario.is_active = True
        usuario.set_password(password_temporal)
        usuario.save()

        messages.success(
            request,
            f"El usuario {usuario.username} ha sido reactivado. Se enviaron las nuevas credenciales a {usuario.email}."
        )

    except Exception as e:
        print(f"DEBUG: Error al enviar correo de reactivación por Brevo: {e}")
        messages.error(
            request,
            f"No se reactivó el usuario porque no se pudo enviar el correo: {e}"
        )

    return redirect('list_personal')

@login_required
@only_director
def eliminar_personal_fisico(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    
    if usuario == request.user:
        messages.error(request, "Error crítico: No puedes eliminar tu propia cuenta.")
        return redirect('/personal/?inactivos=true')
        
    nombre = usuario.username

    usuario.delete() 
    
    messages.success(request, f"¡Completado! El usuario '{nombre}' ha sido eliminado definitivamente de la base de datos.")
    
    return redirect('/personal/?inactivos=true')

@login_required
@only_administrative
def dashboard(request):
    gestion_activa = Gestion.objects.filter(estado=True).first()

    total_estudiantes = Estudiante.objects.filter(
        estado=True
    ).count()

    inscripciones_activas = 0
    cupos_disponibles = 0

    if gestion_activa:
        inscripciones_activas = Inscripcion.objects.filter(
            gestion=gestion_activa,
            estado=True
        ).count()

        paralelos = Paralelo.objects.filter(
            estado=True
        )

        for paralelo in paralelos:
            inscritos = Inscripcion.objects.filter(
                paralelo=paralelo,
                gestion=gestion_activa,
                estado=True
            ).count()

            cupos_disponibles += max(paralelo.cupo_max - inscritos, 0)

    context = {
        'total_estudiantes': total_estudiantes,
        'inscripciones_activas': inscripciones_activas,
        'cupos_disponibles': cupos_disponibles,
        'gestion_activa': gestion_activa,
    }

    return render(request, 'registration/dashboard.html', context)

@login_required
@only_administrative
def reportes(request):
    from django.db.models import OuterRef, Exists, Q
    from django.core.paginator import Paginator

    gestion_activa = Gestion.objects.filter(estado=True).first()

    query = request.GET.get('q', '').strip()
    genero_filtro = request.GET.get('genero', '')
    estado_inscripcion = request.GET.get('inscripcion', '')
    incluir_inactivos = request.GET.get('inactivos') == 'on'

    estudiantes = Estudiante.objects.all().order_by('apellido_paterno', 'apellido_materno', 'nombres')

    if not incluir_inactivos:
        estudiantes = estudiantes.filter(estado=True)

    if query:
        estudiantes = estudiantes.filter(
            Q(cedula_identidad__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellido_paterno__icontains=query) |
            Q(apellido_materno__icontains=query)
        )

    if genero_filtro:
        estudiantes = estudiantes.filter(genero=genero_filtro)

    inscripcion_actual = Inscripcion.objects.filter(
        estudiante=OuterRef('pk'),
        estado=True
    )
    if gestion_activa:
        inscripcion_actual = inscripcion_actual.filter(gestion=gestion_activa)

    estudiantes = estudiantes.annotate(
        tiene_inscripcion=Exists(inscripcion_actual)
    )

    if estado_inscripcion == 'con':
        estudiantes = estudiantes.filter(tiene_inscripcion=True)
    elif estado_inscripcion == 'sin':
        estudiantes = estudiantes.filter(tiene_inscripcion=False)

    inscripciones = Inscripcion.objects.filter(
        estudiante__in=estudiantes,
        estado=True
    ).select_related('paralelo__grado__nivel', 'gestion')

    insc_por_estudiante = {i.estudiante_id: i for i in inscripciones}

    filas = []
    for est in estudiantes:
        filas.append({
            'estudiante': est,
            'inscripcion': insc_por_estudiante.get(est.cedula_identidad),
        })

    total = estudiantes.count()
    con_inscripcion = sum(1 for e in estudiantes if e.tiene_inscripcion)
    sin_inscripcion = total - con_inscripcion

    paginator = Paginator(filas, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    from django.db.models import Count

    gestiones = Gestion.objects.all().order_by('-anio')

    niveles = Nivel.objects.filter(estado=True).annotate(
        total_estudiantes=Count('grados__paralelos__inscripcion', filter=Q(grados__paralelos__inscripcion__estado=True))
    )

    grados = Grado.objects.filter(estado=True).annotate(
        total_estudiantes=Count('paralelos__inscripcion', filter=Q(paralelos__inscripcion__estado=True))
    ).select_related('nivel').order_by('nivel__nombre', 'nombre')

    paralelos = Paralelo.objects.filter(estado=True).annotate(
        total_estudiantes=Count('inscripcion', filter=Q(inscripcion__estado=True))
    ).select_related('grado__nivel').order_by('grado__nivel__nombre', 'grado__nombre', 'letra')

    data_niveles = {
        'labels': [n.nombre for n in niveles],
        'data': [n.total_estudiantes for n in niveles],
    }

    data_grados = {
        'labels': [f"{g.nivel.nombre[:4]} - {g.nombre}" for g in grados],
        'data': [g.total_estudiantes for g in grados],
    }

    paralelos_filtrados = [p for p in paralelos if p.total_estudiantes > 0]
    data_paralelos = {
        'labels': [f"{p.grado.nombre} '{p.letra}'" for p in paralelos_filtrados],
        'data': [p.total_estudiantes for p in paralelos_filtrados],
    }

    insc_por_gestion = Inscripcion.objects.filter(estado=True).values('gestion__anio').annotate(
        total=Count('id')
    ).order_by('gestion__anio')

    data_gestion = {
        'labels': [str(i['gestion__anio']) for i in insc_por_gestion],
        'data': [i['total'] for i in insc_por_gestion],
    }

    total_estudiantes_activos = Estudiante.objects.filter(estado=True).count()
    total_hombres = Estudiante.objects.filter(estado=True, genero='M').count()
    total_mujeres = Estudiante.objects.filter(estado=True, genero='F').count()

    ins_query = request.GET.get('q_ins', '').strip()
    gestion_filtro = request.GET.get('gestion', '')
    estado_doc_filtro = request.GET.get('estado_doc', '')
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    inscripciones = Inscripcion.objects.filter(estado=True).select_related(
        'estudiante', 'paralelo__grado__nivel', 'gestion', 'usuario'
    ).order_by('-gestion__anio', 'paralelo__grado__nivel__nombre', 'paralelo__grado__nombre', 'paralelo__letra', 'estudiante__apellido_paterno')

    if ins_query:
        inscripciones = inscripciones.filter(
            Q(estudiante__cedula_identidad__icontains=ins_query) |
            Q(estudiante__nombres__icontains=ins_query) |
            Q(estudiante__apellido_paterno__icontains=ins_query)
        )
    if gestion_filtro:
        inscripciones = inscripciones.filter(gestion_id=gestion_filtro)
    if estado_doc_filtro:
        inscripciones = inscripciones.filter(estado_documental=estado_doc_filtro)
    if fecha_desde:
        inscripciones = inscripciones.filter(fecha_registro__gte=fecha_desde)
    if fecha_hasta:
        inscripciones = inscripciones.filter(fecha_registro__lte=fecha_hasta)

    total_inscripciones = inscripciones.count()
    doc_completa = inscripciones.filter(estado_documental='completa').count()
    doc_pendiente = inscripciones.filter(estado_documental='pendiente').count()

    insc_paginator = Paginator(inscripciones, 15)
    insc_page = request.GET.get('page_ins', 1)
    insc_page_obj = insc_paginator.get_page(insc_page)

    gestiones_opciones = Gestion.objects.all().order_by('-anio')

    doc_choices = Inscripcion.ESTADO_DOCUMENTAL_CHOICES

    q_doc = request.GET.get('q_doc', '').strip()
    gestion_doc_filtro = request.GET.get('gestion_doc', '')
    estado_doc_filtro_doc = request.GET.get('estado_doc_doc', '')

    docs = Inscripcion.objects.filter(estado=True).select_related(
        'estudiante', 'paralelo__grado__nivel', 'gestion'
    ).order_by('-gestion__anio', 'estudiante__apellido_paterno')

    if q_doc:
        docs = docs.filter(
            Q(estudiante__cedula_identidad__icontains=q_doc) |
            Q(estudiante__nombres__icontains=q_doc) |
            Q(estudiante__apellido_paterno__icontains=q_doc)
        )
    if gestion_doc_filtro:
        docs = docs.filter(gestion_id=gestion_doc_filtro)
    if estado_doc_filtro_doc:
        docs = docs.filter(estado_documental=estado_doc_filtro_doc)

    total_docs = docs.count()
    doc_ok = docs.filter(estado_documental='completa').count()
    doc_pend = docs.filter(estado_documental='pendiente').count()
    doc_venc = docs.filter(estado_documental='vencida').count()

    doc_paginator = Paginator(docs, 15)
    doc_page = request.GET.get('page_doc', 1)
    doc_page_obj = doc_paginator.get_page(doc_page)

    curso_gestion_filtro = request.GET.get('curso_gestion', '')
    cursos_nivel = Nivel.objects.filter(estado=True).order_by('nombre')
    cursos_data = []
    for nivel in cursos_nivel:
        grados = Grado.objects.filter(estado=True, nivel=nivel).order_by('nombre')
        for grado in grados:
            paralelos = Paralelo.objects.filter(estado=True, grado=grado).order_by('letra')
            for paralelo in paralelos:
                qs = Inscripcion.objects.filter(paralelo=paralelo, estado=True)
                if curso_gestion_filtro:
                    qs = qs.filter(gestion_id=curso_gestion_filtro)
                insc_count = qs.count()
                cupo = paralelo.cupo_max
                cursos_data.append({
                    'nivel': nivel.nombre,
                    'grado': grado.nombre,
                    'paralelo': paralelo.letra,
                    'inscritos': insc_count,
                    'cupo': cupo,
                    'disponibles': max(cupo - insc_count, 0),
                })

    context = {
        'filas': page_obj,
        'gestion_activa': gestion_activa,
        'total': total,
        'con_inscripcion': con_inscripcion,
        'sin_inscripcion': sin_inscripcion,
        'query': query,
        'genero_filtro': genero_filtro,
        'estado_inscripcion': estado_inscripcion,
        'incluir_inactivos': incluir_inactivos,
        'page_obj': page_obj,
        'data_niveles': data_niveles,
        'data_grados': data_grados,
        'data_paralelos': data_paralelos,
        'data_gestion': data_gestion,
        'total_estudiantes_activos': total_estudiantes_activos,
        'total_hombres': total_hombres,
        'total_mujeres': total_mujeres,
        'inscripciones': insc_page_obj,
        'total_inscripciones': total_inscripciones,
        'doc_completa': doc_completa,
        'doc_pendiente': doc_pendiente,
        'ins_query': ins_query,
        'gestion_filtro': gestion_filtro,
        'estado_doc_filtro': estado_doc_filtro,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'gestiones_opciones': gestiones_opciones,
        'doc_choices': doc_choices,
        'docs': doc_page_obj,
        'total_docs': total_docs,
        'doc_ok': doc_ok,
        'doc_pend': doc_pend,
        'doc_venc': doc_venc,
        'q_doc': q_doc,
        'gestion_doc_filtro': gestion_doc_filtro,
        'estado_doc_filtro_doc': estado_doc_filtro_doc,
        'cursos_data': cursos_data,
        'curso_gestion_filtro': curso_gestion_filtro,
        'total_cursos': len(cursos_data),
        'total_inscritos_cursos': sum(c['inscritos'] for c in cursos_data),
        'total_disponibles_cursos': sum(c['disponibles'] for c in cursos_data),
    }

    return render(request, 'registration/reportes.html', context)


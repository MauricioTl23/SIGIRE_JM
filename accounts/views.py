import random
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Count, Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator

from academic.models import Gestion, Grado, Nivel, Paralelo
from enrollment.models import Inscripcion
from students.models import Estudiante

from .decorators import only_administrative, only_director
from .email_api import enviar_correo_brevo
from .forms import CustomPasswordChangeForm, RegistroPersonalForm
from .models import User


# ============================================================
# VISTA PÚBLICA
# ============================================================

def home(request):
    """
    Muestra la página principal pública del sistema.

    Esta vista no requiere que el usuario haya iniciado sesión.
    Generalmente se usa como página de bienvenida o presentación
    institucional del sistema.
    """

    return render(request, "registration/home.html")


# ============================================================
# GESTIÓN DE PERSONAL ADMINISTRATIVO
# ============================================================

@login_required
@only_director
def list_personal(request):
    """
    Lista el personal administrativo registrado en el sistema.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Funcionalidades:
    - Mostrar personal activo.
    - Mostrar personal inactivo.
    - Buscar por C.I., nombre, apellido o celular.
    - Filtrar por rol.

    Template:
    - registration/list_personal.html
    """

    # Determina si se deben mostrar usuarios inactivos.
    mostrar_inactivos = request.GET.get("inactivos") == "true"

    # Obtiene el texto escrito en el buscador.
    query_busqueda = request.GET.get("q", "").strip()

    # Obtiene el rol seleccionado en el filtro.
    rol_filtro = request.GET.get("rol", "")

    # Se consultan usuarios activos o inactivos según el filtro seleccionado.
    if mostrar_inactivos:
        personal = User.objects.filter(is_active=False)
    else:
        personal = User.objects.filter(is_active=True)

    # Si existe texto de búsqueda, se filtra por varios campos.
    if query_busqueda:
        personal = personal.filter(
            Q(cedula_identidad__icontains=query_busqueda)
            | Q(first_name__icontains=query_busqueda)
            | Q(last_name__icontains=query_busqueda)
            | Q(celular__icontains=query_busqueda)
        )

    # Si se seleccionó un rol, se filtra el personal por ese rol.
    if rol_filtro:
        personal = personal.filter(rol=rol_filtro)

    context = {
        "personal": personal,
        "mostrar_inactivos": mostrar_inactivos,
        "query_busqueda": query_busqueda,
        "rol_filtro": rol_filtro,
    }

    return render(request, "registration/list_personal.html", context)


@login_required
@only_director
def registrar_personal(request):
    """
    Registra un nuevo usuario administrativo en el sistema.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Flujo:
    1. Recibe los datos del formulario.
    2. Valida la información ingresada.
    3. Genera automáticamente un nombre de usuario.
    4. Genera una contraseña temporal.
    5. Envía las credenciales por correo mediante Brevo.
    6. Guarda el usuario solo si el correo fue enviado correctamente.

    Template:
    - registration/form_personal.html
    """

    if request.method == "POST":
        form = RegistroPersonalForm(request.POST)

        if form.is_valid():
            # Se crea el usuario en memoria, pero todavía no se guarda en BD.
            nuevo_usuario = form.save(commit=False)

            # Se toma el primer nombre para generar el username.
            nombre_raw = (
                nuevo_usuario.first_name.split()[0]
                if nuevo_usuario.first_name
                else "User"
            )
            nombre = nombre_raw.capitalize()

            # Se toman las iniciales de los apellidos.
            apellidos = (
                nuevo_usuario.last_name.split()
                if nuevo_usuario.last_name
                else ["X"]
            )
            iniciales = "".join([a[0].upper() for a in apellidos])

            def generar_propuesta():
                """
                Genera una propuesta de nombre de usuario.

                Formato:
                Nombre + iniciales de apellidos + 3 dígitos aleatorios.

                Ejemplo:
                JuanPL482
                """

                digitos = "".join(random.choices(string.digits, k=3))
                return f"{nombre}{iniciales}{digitos}"

            # Se genera una primera propuesta de username.
            username_final = generar_propuesta()

            # Si el username ya existe, se genera otro hasta encontrar uno único.
            while User.objects.filter(username=username_final).exists():
                username_final = generar_propuesta()

            # Se asigna el username generado al nuevo usuario.
            nuevo_usuario.username = username_final

            # Se genera una contraseña temporal aleatoria.
            password_temporal = get_random_string(length=10)

            # Se cifra la contraseña antes de guardarla.
            nuevo_usuario.set_password(password_temporal)

            asunto = "Bienvenido al Sistema - UE Jesús María"

            mensaje = (
                f"Hola {nuevo_usuario.first_name},\n\n"
                f"Tu cuenta administrativa ha sido creada.\n"
                f"Usuario: {username_final}\n"
                f"Contraseña temporal: {password_temporal}\n\n"
                f"Por seguridad, cambia tu contraseña al ingresar por primera vez."
            )

            try:
                # Se envían las credenciales por correo antes de guardar el usuario.
                enviar_correo_brevo(
                    destinatario_email=nuevo_usuario.email,
                    destinatario_nombre=nuevo_usuario.first_name,
                    asunto=asunto,
                    mensaje=mensaje,
                )

                # Si el correo fue enviado correctamente, recién se guarda el usuario.
                nuevo_usuario.save()

                messages.success(
                    request,
                    f"Personal registrado. Credenciales enviadas a {nuevo_usuario.email}",
                )

                return redirect("list_personal")

            except Exception as e:
                # Si el correo falla, no se guarda el usuario.
                print(f"DEBUG: Error al enviar correo: {e}")

                messages.error(
                    request,
                    f"No se registró el usuario porque no se pudo enviar el correo: {e}",
                )

    else:
        # Si la petición es GET, se muestra el formulario vacío.
        form = RegistroPersonalForm()

    context = {
        "form": form,
    }

    return render(request, "registration/form_personal.html", context)


@login_required
@only_director
def editar_personal(request, pk):
    """
    Edita los datos de un usuario administrativo existente.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Nota:
    En el formulario RegistroPersonalForm se bloquean los campos sensibles
    como cédula de identidad, complemento y expedido cuando el usuario
    ya existe.

    Template:
    - registration/form_personal.html
    """

    # Busca el usuario por su clave primaria. Si no existe, devuelve error 404.
    usuario = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        # Se carga el formulario con los datos enviados y la instancia existente.
        form = RegistroPersonalForm(request.POST, instance=usuario)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"Datos de {usuario.get_full_name()} actualizados.",
            )

            return redirect("list_personal")

    else:
        # Si la petición es GET, se muestra el formulario con los datos actuales.
        form = RegistroPersonalForm(instance=usuario)

    context = {
        "form": form,
        "edit_mode": True,
        "usuario": usuario,
    }

    return render(request, "registration/form_personal.html", context)


@login_required
@only_director
def eliminar_personal(request, pk):
    """
    Desactiva un usuario administrativo mediante borrado lógico.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Importante:
    Esta vista no elimina el registro de la base de datos.
    Solo cambia el estado del usuario a inactivo mediante is_active=False.

    Esto permite conservar historial y trazabilidad.
    """

    usuario = get_object_or_404(User, pk=pk)

    # Evita que el director desactive su propia cuenta.
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")

    else:
        # Borrado lógico: se desactiva al usuario sin eliminarlo de la BD.
        usuario.is_active = False
        usuario.save()

        messages.warning(
            request,
            f"El usuario {usuario.username} ha sido desactivado.",
        )

    return redirect("list_personal")


@login_required
@only_director
def reactivar_personal(request, pk):
    """
    Reactiva una cuenta administrativa previamente desactivada.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Flujo:
    1. Busca el usuario.
    2. Genera una nueva contraseña temporal.
    3. Envía las nuevas credenciales por correo.
    4. Si el correo se envía correctamente, reactiva la cuenta.
    """

    usuario = get_object_or_404(User, pk=pk)

    # Se genera una nueva contraseña temporal.
    password_temporal = get_random_string(length=10)

    asunto = "Reactivación de Cuenta - UE Jesús María"

    mensaje = (
        f"Hola {usuario.first_name},\n\n"
        f"Tu cuenta administrativa ha sido reactivada en el sistema.\n"
        f"Usuario: {usuario.username}\n"
        f"Nueva contraseña temporal: {password_temporal}\n\n"
        f"Por seguridad, te pedimos que cambies tu contraseña inmediatamente al ingresar."
    )

    try:
        # Se envía la nueva contraseña por correo.
        enviar_correo_brevo(
            destinatario_email=usuario.email,
            destinatario_nombre=usuario.first_name,
            asunto=asunto,
            mensaje=mensaje,
        )

        # Si el correo fue enviado correctamente, se reactiva la cuenta.
        usuario.is_active = True
        usuario.set_password(password_temporal)
        usuario.save()

        messages.success(
            request,
            f"El usuario {usuario.username} ha sido reactivado. "
            f"Se enviaron las nuevas credenciales a {usuario.email}.",
        )

    except Exception as e:
        # Si falla el correo, no se reactiva la cuenta.
        print(f"DEBUG: Error al enviar correo de reactivación por Brevo: {e}")

        messages.error(
            request,
            f"No se reactivó el usuario porque no se pudo enviar el correo: {e}",
        )

    return redirect("list_personal")


@login_required
@only_director
def eliminar_personal_fisico(request, pk):
    """
    Elimina definitivamente un usuario administrativo de la base de datos.

    Acceso:
    - Solo usuarios autenticados.
    - Solo usuarios con rol Director.

    Diferencia con eliminar_personal:
    - eliminar_personal: solo desactiva el usuario.
    - eliminar_personal_fisico: borra el registro definitivamente.

    Esta función debe usarse con cuidado porque elimina información real
    de la base de datos.
    """

    usuario = get_object_or_404(User, pk=pk)

    # Evita que el director elimine definitivamente su propia cuenta.
    if usuario == request.user:
        messages.error(
            request,
            "Error crítico: No puedes eliminar tu propia cuenta.",
        )

        return redirect("/personal/?inactivos=true")

    nombre = usuario.username

    # Eliminación física del usuario.
    usuario.delete()

    messages.success(
        request,
        f"¡Completado! El usuario '{nombre}' ha sido eliminado definitivamente de la base de datos.",
    )

    return redirect("/personal/?inactivos=true")


# ============================================================
# CAMBIO DE CONTRASEÑA
# ============================================================

class UserPasswordChangeView(PasswordChangeView):
    """
    Vista para cambio de contraseña del usuario autenticado.

    Hereda de PasswordChangeView de Django y utiliza un formulario
    personalizado para mantener el diseño visual del sistema.

    Template:
    - registration/change_password.html

    Redirección exitosa:
    - dashboard
    """

    form_class = CustomPasswordChangeForm
    template_name = "registration/change_password.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        """
        Se ejecuta cuando el formulario de cambio de contraseña es válido.

        Muestra un mensaje de éxito y luego continúa con el flujo normal
        de PasswordChangeView.
        """

        messages.success(
            self.request,
            "¡Tu contraseña ha sido actualizada con éxito!",
        )

        return super().form_valid(form)


# ============================================================
# DASHBOARD
# ============================================================

@login_required
@only_administrative
def dashboard(request):
    """
    Muestra el panel principal del sistema.

    Acceso:
    - Director.
    - Secretaría.

    Indicadores calculados:
    - Total de estudiantes activos.
    - Inscripciones activas de la gestión vigente.
    - Cupos disponibles.
    - Gestión activa.

    Template:
    - registration/dashboard.html
    """

    # Obtiene la gestión académica activa.
    gestion_activa = Gestion.objects.filter(estado=True).first()

    # Cuenta todos los estudiantes activos.
    total_estudiantes = Estudiante.objects.filter(
        estado=True
    ).count()

    # Valores iniciales por si no existe una gestión activa.
    inscripciones_activas = 0
    cupos_disponibles = 0

    if gestion_activa:
        # Cuenta las inscripciones activas de la gestión actual.
        inscripciones_activas = Inscripcion.objects.filter(
            gestion=gestion_activa,
            estado=True,
        ).count()

        # Consulta todos los paralelos activos.
        paralelos = Paralelo.objects.filter(
            estado=True
        )

        # Calcula los cupos disponibles sumando la disponibilidad de cada paralelo.
        for paralelo in paralelos:
            inscritos = Inscripcion.objects.filter(
                paralelo=paralelo,
                gestion=gestion_activa,
                estado=True,
            ).count()

            # Se usa max para evitar cupos negativos.
            cupos_disponibles += max(paralelo.cupo_max - inscritos, 0)

    context = {
        "total_estudiantes": total_estudiantes,
        "inscripciones_activas": inscripciones_activas,
        "cupos_disponibles": cupos_disponibles,
        "gestion_activa": gestion_activa,
    }

    return render(request, "registration/dashboard.html", context)


# ============================================================
# REPORTES
# ============================================================

@login_required
@only_administrative
def reportes(request):
    """
    Genera la vista general de reportes del sistema.

    Acceso:
    - Director.
    - Secretaría.

    Esta vista concentra diferentes bloques de información:

    1. Reporte de estudiantes:
       - Lista estudiantes activos o inactivos.
       - Filtra por búsqueda, género y estado de inscripción.
       - Pagina los resultados.

    2. Datos para gráficos:
       - Estudiantes por nivel.
       - Estudiantes por grado.
       - Estudiantes por paralelo.
       - Inscripciones por gestión.

    3. Reporte de inscripciones:
       - Lista inscripciones activas.
       - Filtra por estudiante, gestión, estado documental y fechas.

    4. Reporte documental:
       - Muestra el estado documental de las inscripciones.

    5. Reporte de cursos:
       - Calcula inscritos, cupo máximo y cupos disponibles por paralelo.

    Template:
    - registration/reportes.html
    """

    # ========================================================
    # GESTIÓN ACTIVA
    # ========================================================

    gestion_activa = Gestion.objects.filter(estado=True).first()

    # ========================================================
    # FILTROS DEL REPORTE DE ESTUDIANTES
    # ========================================================

    query = request.GET.get("q", "").strip()
    genero_filtro = request.GET.get("genero", "")
    estado_inscripcion = request.GET.get("inscripcion", "")
    incluir_inactivos = request.GET.get("inactivos") == "on"

    # Consulta base de estudiantes ordenados alfabéticamente.
    estudiantes = Estudiante.objects.all().order_by(
        "apellido_paterno",
        "apellido_materno",
        "nombres",
    )

    # Por defecto se muestran solo estudiantes activos.
    if not incluir_inactivos:
        estudiantes = estudiantes.filter(estado=True)

    # Filtro de búsqueda por C.I., nombres o apellidos.
    if query:
        estudiantes = estudiantes.filter(
            Q(cedula_identidad__icontains=query)
            | Q(nombres__icontains=query)
            | Q(apellido_paterno__icontains=query)
            | Q(apellido_materno__icontains=query)
        )

    # Filtro por género.
    if genero_filtro:
        estudiantes = estudiantes.filter(genero=genero_filtro)

    # Subconsulta para verificar si el estudiante tiene inscripción activa.
    inscripcion_actual = Inscripcion.objects.filter(
        estudiante=OuterRef("pk"),
        estado=True,
    )

    # Si existe gestión activa, la validación de inscripción se limita a esa gestión.
    if gestion_activa:
        inscripcion_actual = inscripcion_actual.filter(gestion=gestion_activa)

    # Agrega un campo booleano calculado: tiene_inscripcion.
    estudiantes = estudiantes.annotate(
        tiene_inscripcion=Exists(inscripcion_actual)
    )

    # Filtra estudiantes según si tienen o no inscripción.
    if estado_inscripcion == "con":
        estudiantes = estudiantes.filter(tiene_inscripcion=True)

    elif estado_inscripcion == "sin":
        estudiantes = estudiantes.filter(tiene_inscripcion=False)

    # Consulta inscripciones activas de los estudiantes filtrados.
    inscripciones = Inscripcion.objects.filter(
        estudiante__in=estudiantes,
        estado=True,
    ).select_related(
        "paralelo__grado__nivel",
        "gestion",
    )

    # Diccionario para acceder rápido a la inscripción de cada estudiante.
    insc_por_estudiante = {
        i.estudiante_id: i
        for i in inscripciones
    }

    # Arma filas combinando estudiante e inscripción.
    filas = []

    for est in estudiantes:
        filas.append({
            "estudiante": est,
            "inscripcion": insc_por_estudiante.get(est.cedula_identidad),
        })

    # Totales del reporte de estudiantes.
    total = estudiantes.count()
    con_inscripcion = sum(1 for e in estudiantes if e.tiene_inscripcion)
    sin_inscripcion = total - con_inscripcion

    # Paginación del reporte de estudiantes.
    paginator = Paginator(filas, 15)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # ========================================================
    # DATOS PARA GRÁFICOS GENERALES
    # ========================================================

    gestiones = Gestion.objects.all().order_by("-anio")

    # Total de inscripciones activas agrupadas por nivel.
    niveles = Nivel.objects.filter(estado=True).annotate(
        total_estudiantes=Count(
            "grados__paralelos__inscripcion",
            filter=Q(grados__paralelos__inscripcion__estado=True),
        )
    )

    # Total de inscripciones activas agrupadas por grado.
    grados = Grado.objects.filter(estado=True).annotate(
        total_estudiantes=Count(
            "paralelos__inscripcion",
            filter=Q(paralelos__inscripcion__estado=True),
        )
    ).select_related(
        "nivel"
    ).order_by(
        "nivel__nombre",
        "nombre",
    )

    # Total de inscripciones activas agrupadas por paralelo.
    paralelos = Paralelo.objects.filter(estado=True).annotate(
        total_estudiantes=Count(
            "inscripcion",
            filter=Q(inscripcion__estado=True),
        )
    ).select_related(
        "grado__nivel"
    ).order_by(
        "grado__nivel__nombre",
        "grado__nombre",
        "letra",
    )

    # Datos para gráfico de estudiantes por nivel.
    data_niveles = {
        "labels": [n.nombre for n in niveles],
        "data": [n.total_estudiantes for n in niveles],
    }

    # Datos para gráfico de estudiantes por grado.
    data_grados = {
        "labels": [
            f"{g.nivel.nombre[:4]} - {g.nombre}"
            for g in grados
        ],
        "data": [
            g.total_estudiantes
            for g in grados
        ],
    }

    # Se muestran solo paralelos que tienen estudiantes inscritos.
    paralelos_filtrados = [
        p
        for p in paralelos
        if p.total_estudiantes > 0
    ]

    # Datos para gráfico de estudiantes por paralelo.
    data_paralelos = {
        "labels": [
            f"{p.grado.nombre} '{p.letra}'"
            for p in paralelos_filtrados
        ],
        "data": [
            p.total_estudiantes
            for p in paralelos_filtrados
        ],
    }

    # Total de inscripciones activas por gestión.
    insc_por_gestion = Inscripcion.objects.filter(
        estado=True
    ).values(
        "gestion__anio"
    ).annotate(
        total=Count("id")
    ).order_by(
        "gestion__anio"
    )

    # Datos para gráfico de inscripciones por gestión.
    data_gestion = {
        "labels": [
            str(i["gestion__anio"])
            for i in insc_por_gestion
        ],
        "data": [
            i["total"]
            for i in insc_por_gestion
        ],
    }

    # Totales generales de estudiantes activos.
    total_estudiantes_activos = Estudiante.objects.filter(
        estado=True
    ).count()

    total_hombres = Estudiante.objects.filter(
        estado=True,
        genero="M",
    ).count()

    total_mujeres = Estudiante.objects.filter(
        estado=True,
        genero="F",
    ).count()

    # ========================================================
    # REPORTE DE INSCRIPCIONES
    # ========================================================

    ins_query = request.GET.get("q_ins", "").strip()
    gestion_filtro = request.GET.get("gestion", "")
    estado_doc_filtro = request.GET.get("estado_doc", "")
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()

    # Consulta base de inscripciones activas.
    inscripciones = Inscripcion.objects.filter(
        estado=True
    ).select_related(
        "estudiante",
        "paralelo__grado__nivel",
        "gestion",
        "usuario",
    ).order_by(
        "-gestion__anio",
        "paralelo__grado__nivel__nombre",
        "paralelo__grado__nombre",
        "paralelo__letra",
        "estudiante__apellido_paterno",
    )

    # Filtro por datos del estudiante.
    if ins_query:
        inscripciones = inscripciones.filter(
            Q(estudiante__cedula_identidad__icontains=ins_query)
            | Q(estudiante__nombres__icontains=ins_query)
            | Q(estudiante__apellido_paterno__icontains=ins_query)
        )

    # Filtro por gestión académica.
    if gestion_filtro:
        inscripciones = inscripciones.filter(gestion_id=gestion_filtro)

    # Filtro por estado documental.
    if estado_doc_filtro:
        inscripciones = inscripciones.filter(
            estado_documental=estado_doc_filtro
        )

    # Filtro por fecha desde.
    if fecha_desde:
        inscripciones = inscripciones.filter(
            fecha_registro__gte=fecha_desde
        )

    # Filtro por fecha hasta.
    if fecha_hasta:
        inscripciones = inscripciones.filter(
            fecha_registro__lte=fecha_hasta
        )

    # Totales del reporte de inscripciones.
    total_inscripciones = inscripciones.count()

    doc_completa = inscripciones.filter(
        estado_documental="completa"
    ).count()

    doc_pendiente = inscripciones.filter(
        estado_documental="pendiente"
    ).count()

    # Paginación del reporte de inscripciones.
    insc_paginator = Paginator(inscripciones, 15)
    insc_page = request.GET.get("page_ins", 1)
    insc_page_obj = insc_paginator.get_page(insc_page)

    # Opciones para filtros de gestión y estado documental.
    gestiones_opciones = Gestion.objects.all().order_by("-anio")
    doc_choices = Inscripcion.ESTADO_DOCUMENTAL_CHOICES

    # ========================================================
    # REPORTE DOCUMENTAL
    # ========================================================

    q_doc = request.GET.get("q_doc", "").strip()
    gestion_doc_filtro = request.GET.get("gestion_doc", "")
    estado_doc_filtro_doc = request.GET.get("estado_doc_doc", "")

    # Consulta base para reporte documental.
    docs = Inscripcion.objects.filter(
        estado=True
    ).select_related(
        "estudiante",
        "paralelo__grado__nivel",
        "gestion",
    ).order_by(
        "-gestion__anio",
        "estudiante__apellido_paterno",
    )

    # Filtro por datos del estudiante.
    if q_doc:
        docs = docs.filter(
            Q(estudiante__cedula_identidad__icontains=q_doc)
            | Q(estudiante__nombres__icontains=q_doc)
            | Q(estudiante__apellido_paterno__icontains=q_doc)
        )

    # Filtro por gestión.
    if gestion_doc_filtro:
        docs = docs.filter(gestion_id=gestion_doc_filtro)

    # Filtro por estado documental.
    if estado_doc_filtro_doc:
        docs = docs.filter(
            estado_documental=estado_doc_filtro_doc
        )

    # Totales documentales.
    total_docs = docs.count()

    doc_ok = docs.filter(
        estado_documental="completa"
    ).count()

    doc_pend = docs.filter(
        estado_documental="pendiente"
    ).count()

    doc_venc = docs.filter(
        estado_documental="vencida"
    ).count()

    # Paginación del reporte documental.
    doc_paginator = Paginator(docs, 15)
    doc_page = request.GET.get("page_doc", 1)
    doc_page_obj = doc_paginator.get_page(doc_page)

    # ========================================================
    # REPORTE DE CURSOS Y CUPOS
    # ========================================================

    curso_gestion_filtro = request.GET.get("curso_gestion", "")

    # Consulta niveles activos.
    cursos_nivel = Nivel.objects.filter(
        estado=True
    ).order_by(
        "nombre"
    )

    cursos_data = []

    # Recorre nivel, grado y paralelo para calcular inscritos y cupos.
    for nivel in cursos_nivel:
        grados = Grado.objects.filter(
            estado=True,
            nivel=nivel,
        ).order_by(
            "nombre"
        )

        for grado in grados:
            paralelos = Paralelo.objects.filter(
                estado=True,
                grado=grado,
            ).order_by(
                "letra"
            )

            for paralelo in paralelos:
                # Consulta inscripciones activas del paralelo.
                qs = Inscripcion.objects.filter(
                    paralelo=paralelo,
                    estado=True,
                )

                # Si se seleccionó una gestión, se filtra por esa gestión.
                if curso_gestion_filtro:
                    qs = qs.filter(gestion_id=curso_gestion_filtro)

                insc_count = qs.count()
                cupo = paralelo.cupo_max

                cursos_data.append({
                    "nivel": nivel.nombre,
                    "grado": grado.nombre,
                    "paralelo": paralelo.letra,
                    "paralelo_id": paralelo.id,
                    "gestion_id": curso_gestion_filtro if curso_gestion_filtro else "",
                    "inscritos": insc_count,
                    "cupo": cupo,
                    "disponibles": max(cupo - insc_count, 0),
                })

    # ========================================================
    # CONTEXTO FINAL PARA EL TEMPLATE
    # ========================================================

    context = {
        # Reporte de estudiantes
        "filas": page_obj,
        "gestion_activa": gestion_activa,
        "total": total,
        "con_inscripcion": con_inscripcion,
        "sin_inscripcion": sin_inscripcion,
        "query": query,
        "genero_filtro": genero_filtro,
        "estado_inscripcion": estado_inscripcion,
        "incluir_inactivos": incluir_inactivos,
        "page_obj": page_obj,

        # Datos para gráficos
        "data_niveles": data_niveles,
        "data_grados": data_grados,
        "data_paralelos": data_paralelos,
        "data_gestion": data_gestion,

        # Totales generales
        "total_estudiantes_activos": total_estudiantes_activos,
        "total_hombres": total_hombres,
        "total_mujeres": total_mujeres,

        # Reporte de inscripciones
        "inscripciones": insc_page_obj,
        "total_inscripciones": total_inscripciones,
        "doc_completa": doc_completa,
        "doc_pendiente": doc_pendiente,
        "ins_query": ins_query,
        "gestion_filtro": gestion_filtro,
        "estado_doc_filtro": estado_doc_filtro,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "gestiones_opciones": gestiones_opciones,
        "doc_choices": doc_choices,

        # Reporte documental
        "docs": doc_page_obj,
        "total_docs": total_docs,
        "doc_ok": doc_ok,
        "doc_pend": doc_pend,
        "doc_venc": doc_venc,
        "q_doc": q_doc,
        "gestion_doc_filtro": gestion_doc_filtro,
        "estado_doc_filtro_doc": estado_doc_filtro_doc,

        # Reporte de cursos y cupos
        "cursos_data": cursos_data,
        "curso_gestion_filtro": curso_gestion_filtro,
        "total_cursos": len(cursos_data),
        "total_inscritos_cursos": sum(c["inscritos"] for c in cursos_data),
        "total_disponibles_cursos": sum(c["disponibles"] for c in cursos_data),
    }

    return render(request, "registration/reportes.html", context)


# ============================================================
# CONSULTA AJAX DE ESTUDIANTES POR CURSO
# ============================================================

@login_required
@only_administrative
def curso_estudiantes(request, paralelo_id):
    """
    Devuelve los estudiantes inscritos en un paralelo en formato JSON.

    Acceso:
    - Director.
    - Secretaría.

    Uso:
    Esta vista se puede consumir desde JavaScript mediante AJAX/fetch
    para mostrar estudiantes de un curso sin recargar toda la página.

    Parámetros:
    - paralelo_id: identificador del paralelo.

    Filtro opcional por GET:
    - gestion_id

    Respuesta:
    {
        "estudiantes": [
            {
                "nombres": "Juan Pérez López",
                "ci": "1234567"
            }
        ]
    }
    """

    # Obtiene la gestión enviada por GET, si existe.
    gestion_id = request.GET.get("gestion_id", "")

    # Consulta inscripciones activas del paralelo.
    inscripciones = Inscripcion.objects.filter(
        paralelo_id=paralelo_id,
        estado=True,
    ).select_related(
        "estudiante"
    )

    # Si se recibe una gestión, se filtran las inscripciones.
    if gestion_id:
        inscripciones = inscripciones.filter(gestion_id=gestion_id)

    estudiantes = []

    # Se arma una lista simple con nombre completo y C.I.
    for ins in inscripciones:
        est = ins.estudiante

        estudiantes.append({
            "nombres": (
                f"{est.nombres} "
                f"{est.apellido_paterno} "
                f"{est.apellido_materno}"
            ).strip(),
            "ci": est.cedula_identidad,
        })

    return JsonResponse({
        "estudiantes": estudiantes,
    })
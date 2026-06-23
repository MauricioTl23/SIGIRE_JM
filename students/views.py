from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from academic.models import Gestion
from enrollment.models import Inscripcion

from .forms import EditarEstudianteForm, EstudianteForm, TutorForm
from .models import Estudiante, Parentesco, Tutor


# ============================================================
# GESTIÓN DE TUTORES
# ============================================================

@login_required
def registrar_tutor(request):
    """
    Registra un nuevo tutor en el sistema.

    Flujo:
    1. Si la petición es POST, recibe los datos del formulario.
    2. Valida el formulario TutorForm.
    3. Si es válido, guarda el tutor.
    4. Redirige al listado de tutores enviando el ID del nuevo tutor.
    5. Si es GET, muestra el formulario vacío.

    Template:
    - Tutor/form_tutor.html
    """

    if request.method == "POST":
        form = TutorForm(request.POST)

        if form.is_valid():
            # Guarda el tutor en la base de datos.
            tutor = form.save()

            messages.success(
                request,
                "Tutor registrado correctamente."
            )

            # Redirige al listado de tutores y manda el ID del tutor creado.
            # Esto puede servir para seleccionarlo después al registrar un estudiante.
            base_url = reverse("list_tutores")
            return redirect(f"{base_url}?nuevo_tutor_id={tutor.pk}")

        else:
            messages.error(
                request,
                "Error en el formulario. Verifique los datos."
            )

    else:
        # Si no es POST, se muestra un formulario vacío.
        form = TutorForm()

    return render(
        request,
        "Tutor/form_tutor.html",
        {
            "form": form,
        }
    )


@login_required
def list_tutores(request):
    """
    Lista los tutores activos registrados en el sistema.

    Funcionalidades:
    - Buscar tutores por nombres, apellidos, C.I. u ocupación.
    - Mostrar si el tutor tiene estudiantes asociados.
    - Paginar resultados de 15 en 15.

    Template:
    - Tutor/list_tutores.html
    """

    # Obtiene el texto ingresado en el buscador.
    query = request.GET.get("search", "").strip()

    # Subconsulta para verificar si un tutor tiene parentescos asociados.
    parentescos = Parentesco.objects.filter(
        tutor=OuterRef("pk")
    )

    # Consulta tutores activos y agrega un campo calculado:
    # tiene_estudiantes_db = True/False.
    tutores_qs = (
        Tutor.objects
        .filter(estado=True)
        .annotate(tiene_estudiantes_db=Exists(parentescos))
        .order_by("apellidos", "nombres")
    )

    # Si hay texto de búsqueda, se filtra por varios campos.
    if query:
        tutores_qs = tutores_qs.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(cedula_identidad__icontains=query)
            | Q(ocupacion__icontains=query)
        ).distinct()

    # Paginación de tutores.
    paginator = Paginator(tutores_qs, 15)
    page_number = request.GET.get("page")
    tutores = paginator.get_page(page_number)

    return render(
        request,
        "Tutor/list_tutores.html",
        {
            "tutores": tutores,
            "search_query": query,
        }
    )


@login_required
def editar_tutor(request, pk):
    """
    Edita los datos de un tutor existente.

    La cédula de identidad se divide en:
    - ci_nro
    - ci_comp
    - ci_exp

    Esto permite mostrarla correctamente en el formulario, aunque en la base
    de datos esté guardada como un solo texto.

    Template:
    - Tutor/form_tutor.html
    """

    # Busca el tutor. Si no existe, devuelve error 404.
    tutor = get_object_or_404(Tutor, pk=pk)

    # Divide la cédula guardada.
    # Formatos posibles:
    # - 1234567-LP
    # - 1234567-A1-LP
    ci_parts = tutor.cedula_identidad.split("-")

    initial_data = {
        "ci_nro": ci_parts[0],
        "ci_comp": ci_parts[1] if len(ci_parts) == 3 else "",
        "ci_exp": ci_parts[-1],
    }

    if request.method == "POST":
        form = TutorForm(
            request.POST,
            instance=tutor,
            initial=initial_data
        )

        if form.is_valid():
            # Solo guarda si detecta cambios reales.
            if form.has_changed():
                form.save()

                messages.success(
                    request,
                    f"Datos de {tutor.nombres} {tutor.apellidos} actualizados correctamente."
                )

            else:
                messages.info(
                    request,
                    "No se detectaron modificaciones en el formulario."
                )

            return redirect("list_tutores")

        else:
            # Mensaje de depuración para consola.
            print("Errores del formulario:", form.errors)

            messages.error(
                request,
                "Error de validación. Revisa los datos ingresados."
            )

    else:
        form = TutorForm(
            instance=tutor,
            initial=initial_data
        )

    return render(
        request,
        "Tutor/form_tutor.html",
        {
            "form": form,
            "edit_mode": True,
            "tutor": tutor,
        }
    )


@login_required
def eliminar_tutor(request, pk):
    """
    Desactiva un tutor mediante borrado lógico.

    Reglas:
    - No se puede eliminar un tutor si tiene estudiantes asociados.
    - Si no tiene estudiantes, se marca como inactivo.
    - Se registra la fecha de baja.

    No elimina físicamente el registro de la base de datos.
    """

    tutor = get_object_or_404(Tutor, pk=pk)

    # Si el tutor tiene estudiantes asociados, no se permite eliminar.
    if tutor.tiene_estudiantes:
        messages.error(
            request,
            f"El tutor {tutor.nombres} {tutor.apellidos} no se puede eliminar "
            f"porque tiene estudiantes asociados."
        )

        return redirect("list_tutores")

    # Borrado lógico del tutor.
    tutor.estado = False
    tutor.fecha_baja = timezone.now()
    tutor.save()

    messages.warning(
        request,
        f"El tutor {tutor.nombres} fue enviado a la papelera. "
        f"Se eliminará definitivamente en 30 días."
    )

    return redirect("list_tutores")


# ============================================================
# GESTIÓN DE ESTUDIANTES
# ============================================================

@login_required
def list_estudiantes(request):
    """
    Lista estudiantes registrados en el sistema.

    Funcionalidades:
    - Buscar estudiantes por nombre, apellidos o C.I.
    - Filtrar por género.
    - Ver estudiantes activos o inactivos.
    - Usar modo de selección para inscripción.
    - Diferenciar estudiantes con inscripción previa o sin inscripción previa.
    - Paginar resultados de 15 en 15.

    Template:
    - Student/list_estudiantes.html
    """

    # Filtros principales.
    query = request.GET.get("search", "").strip()
    genero_filtro = request.GET.get("genero", "")
    ver_inactivos = request.GET.get("inactivos") == "on"

    # Filtros usados cuando se selecciona estudiante para inscripción.
    modo_seleccion_inscripcion = (
        request.GET.get("modo_seleccion_inscripcion") == "true"
    )
    tipo_inscripcion = request.GET.get("tipo_inscripcion", "")

    # Consulta base de estudiantes.
    estudiantes = Estudiante.objects.all().order_by(
        "apellido_paterno",
        "apellido_materno",
        "nombres"
    )

    # Muestra activos o inactivos según el filtro.
    if ver_inactivos:
        estudiantes = estudiantes.filter(estado=False)
    else:
        estudiantes = estudiantes.filter(estado=True)

    # Obtiene la gestión activa actual.
    gestion_actual = (
        Gestion.objects
        .filter(estado=True)
        .order_by("-anio")
        .first()
    )

    # Busca la gestión anterior a la actual.
    gestion_pasada = None

    if gestion_actual:
        gestion_pasada = (
            Gestion.objects
            .filter(anio__lt=gestion_actual.anio)
            .order_by("-anio")
            .first()
        )

    # Subconsulta para saber si el estudiante tiene alguna inscripción histórica.
    inscripciones_cualquier_gestion = Inscripcion.objects.filter(
        estudiante=OuterRef("pk")
    )

    estudiantes = estudiantes.annotate(
        tiene_alguna_inscripcion=Exists(inscripciones_cualquier_gestion)
    )

    # Si se está usando la pantalla como selector para inscripción,
    # se aplican filtros especiales.
    if modo_seleccion_inscripcion and gestion_actual:

        # Subconsulta para saber si el estudiante ya está inscrito
        # en la gestión actual.
        inscripcion_actual = Inscripcion.objects.filter(
            estudiante=OuterRef("pk"),
            gestion=gestion_actual
        )

        estudiantes = estudiantes.annotate(
            tiene_inscripcion_actual=Exists(inscripcion_actual)
        )

        # Estudiantes completamente nuevos, sin inscripción histórica.
        if tipo_inscripcion == "sin_previa":
            estudiantes = estudiantes.filter(
                tiene_alguna_inscripcion=False
            )

        # Estudiantes que ya tuvieron inscripción previa,
        # pero todavía no están inscritos en la gestión actual.
        elif tipo_inscripcion == "con_previa":
            if gestion_pasada:
                inscripcion_pasada = Inscripcion.objects.filter(
                    estudiante=OuterRef("pk"),
                    gestion=gestion_pasada
                )

                estudiantes = estudiantes.annotate(
                    tiene_inscripcion_pasada=Exists(inscripcion_pasada)
                ).filter(
                    tiene_inscripcion_pasada=True,
                    tiene_inscripcion_actual=False
                )

            else:
                # Si no existe gestión pasada, no hay estudiantes con inscripción previa.
                estudiantes = estudiantes.none()

    # Filtro de búsqueda.
    if query:
        estudiantes = estudiantes.filter(
            Q(nombres__icontains=query)
            | Q(apellido_paterno__icontains=query)
            | Q(apellido_materno__icontains=query)
            | Q(cedula_identidad__icontains=query)
        ).distinct()

    # Filtro por género.
    if genero_filtro:
        estudiantes = estudiantes.filter(genero=genero_filtro)

    # Paginación.
    paginator = Paginator(estudiantes, 15)
    page_number = request.GET.get("page")
    estudiantes = paginator.get_page(page_number)

    return render(
        request,
        "Student/list_estudiantes.html",
        {
            "estudiantes": estudiantes,
            "search_query": query,
            "genero_filter": genero_filtro,
            "ver_inactivos": ver_inactivos,
            "modo_seleccion_inscripcion": modo_seleccion_inscripcion,
            "tipo_inscripcion": tipo_inscripcion,
            "gestion_actual": gestion_actual,
            "gestion_pasada": gestion_pasada,
        }
    )


@login_required
def crear_estudiante(request):
    """
    Registra un nuevo estudiante y lo vincula con un tutor.

    Flujo:
    1. Obtiene el tutor_id desde GET o POST.
    2. Busca el tutor seleccionado.
    3. Si no hay tutor, muestra una pregunta o redirige por seguridad.
    4. Valida el formulario EstudianteForm.
    5. Guarda el estudiante.
    6. Crea la relación de parentesco con el tutor.
    7. Redirige al listado de estudiantes.

    Template:
    - Student/form_student.html
    """

    # El tutor puede llegar desde la URL o desde el formulario.
    tutor_id = request.GET.get("tutor_id") or request.POST.get("tutor_id")

    tutor_guardar = None
    mostrar_pregunta = False

    # Busca el tutor si se recibió tutor_id.
    if tutor_id:
        try:
            tutor_guardar = Tutor.objects.get(pk=tutor_id)

        except Tutor.DoesNotExist:
            tutor_guardar = None

    else:
        # Si no se recibió tutor, el template puede mostrar una pregunta previa.
        mostrar_pregunta = True

    if request.method == "POST":
        form = EstudianteForm(request.POST)

        # Seguridad: no se permite registrar estudiante sin tutor.
        if not tutor_guardar:
            messages.error(
                request,
                "Error de seguridad: Se requiere un tutor para registrar al estudiante."
            )

            return redirect("list_tutores")

        if form.is_valid():
            # Crea el estudiante sin guardar de inmediato.
            nuevo_estudiante = form.save(commit=False)

            # Se asegura que el estudiante quede activo.
            nuevo_estudiante.estado = True
            nuevo_estudiante.save()

            # Tipo de relación con el tutor.
            tipo_relacion = request.POST.get("relacion", "Apoderado")

            # Crea la relación estudiante-tutor.
            Parentesco.objects.create(
                estudiante=nuevo_estudiante,
                tutor=tutor_guardar,
                relacion=tipo_relacion
            )

            messages.success(
                request,
                f"Estudiante {nuevo_estudiante.nombres} y Tutor vinculados correctamente."
            )

            # Redirige al listado con parámetros útiles para resaltar el registro.
            url_destino = reverse("list_estudiantes")

            return redirect(
                f"{url_destino}?registrado_id={nuevo_estudiante.pk}"
                f"&nombre_est={nuevo_estudiante.nombres}"
            )

        else:
            messages.error(
                request,
                "Error en el formulario. Verifique los datos."
            )

    else:
        form = EstudianteForm()

    # Opciones de expedición para el template.
    departamentos = (
        form.fields["ci_exp"].choices
        if "ci_exp" in form.fields
        else []
    )

    context = {
        "form": form,
        "tutor_seleccionado": tutor_guardar,
        "mostrar_pregunta": mostrar_pregunta,
        "departamentos": departamentos,
    }

    return render(
        request,
        "Student/form_student.html",
        context
    )


@login_required
def editar_estudiante(request, pk):
    """
    Edita los datos de un estudiante existente.

    Esta vista:
    - Normaliza la C.I. para mostrarla separada en el template.
    - Separa la dirección en zona, avenida/calle y número.
    - Usa EditarEstudianteForm para modificar datos personales.
    - No modifica la cédula de identidad del estudiante.

    Template:
    - Student/form_student.html
    """

    estudiante = get_object_or_404(Estudiante, pk=pk)

    # ========================================================
    # NORMALIZACIÓN DE CÉDULA DE IDENTIDAD
    # ========================================================

    full_ci = estudiante.cedula_identidad.strip().upper()

    # Cambia espacios por guiones para evitar errores de formato.
    full_ci_norm = full_ci.replace(" ", "-")

    # Elimina guiones dobles si existieran.
    while "--" in full_ci_norm:
        full_ci_norm = full_ci_norm.replace("--", "-")

    partes_ci = full_ci_norm.split("-")

    nro = partes_ci[0] if len(partes_ci) > 0 else ""
    comp = ""
    expedido = ""

    # Formato con complemento: 1234567-A1-LP
    if len(partes_ci) == 3:
        comp = partes_ci[1]
        expedido = partes_ci[2]

    # Formato sin complemento: 1234567-LP
    elif len(partes_ci) == 2:
        expedido = partes_ci[1]

    # ========================================================
    # SEPARACIÓN DE DIRECCIÓN
    # ========================================================

    dir_texto = estudiante.direccion

    calle = ""
    numero = ""
    zona = ""

    # Dirección esperada:
    # Zona, Avenida, N° Número
    if ", " in dir_texto:
        partes_dir = dir_texto.split(", ")

        zona = partes_dir[0] if len(partes_dir) > 0 else ""
        calle = partes_dir[1] if len(partes_dir) > 1 else ""

        if len(partes_dir) > 2:
            numero = partes_dir[2].replace("N° ", "").strip()

    else:
        # Si la dirección no tiene el formato esperado,
        # se coloca todo como calle.
        calle = dir_texto

    # ========================================================
    # PROCESAMIENTO DEL FORMULARIO
    # ========================================================

    if request.method == "POST":
        form = EditarEstudianteForm(
            request.POST,
            instance=estudiante
        )

        if form.is_valid():
            est_modificado = form.save(commit=False)

            # Se reconstruye la dirección desde los campos del formulario.
            zona_post = form.cleaned_data.get("zona", "")
            calle_post = form.cleaned_data.get("avenida", "")
            nro_post = form.cleaned_data.get("num_puerta", "")

            est_modificado.direccion = (
                f"{zona_post}, {calle_post}, N° {nro_post}"
            )

            est_modificado.save()

            messages.success(
                request,
                f"Datos de {est_modificado.nombres} actualizados."
            )

            return redirect("list_estudiantes")

        else:
            # Mensajes de depuración para consola.
            print("\n--- ERRORES EN EDICIÓN ---")
            print(form.errors)
            print("--------------------------\n")

            messages.error(
                request,
                "Error en el formulario. Verifique los datos."
            )

    else:
        form = EditarEstudianteForm(instance=estudiante)

    # Opciones de expedición para mostrar en el template.
    departamentos = [
        ("LP", "La Paz"),
        ("OR", "Oruro"),
        ("PT", "Potosí"),
        ("CB", "Cochabamba"),
        ("SC", "Santa Cruz"),
        ("BN", "Beni"),
        ("PA", "Pando"),
        ("TJ", "Tarija"),
        ("CH", "Chuquisaca"),
    ]

    return render(
        request,
        "Student/form_student.html",
        {
            "form": form,
            "estudiante": estudiante,
            "es_edicion": True,
            "ci_nro_val": nro,
            "ci_comp_val": comp,
            "ci_exp_val": expedido,
            "dir_calle": calle,
            "dir_nro": numero,
            "dir_zona": zona,
            "departamentos": departamentos,
        }
    )


@login_required
def desactivar_estudiante(request, pk):
    """
    Desactiva un estudiante mediante borrado lógico.

    No elimina el registro de la base de datos.
    Solo cambia el campo estado a False.
    """

    estudiante = get_object_or_404(Estudiante, pk=pk)

    estudiante.estado = False
    estudiante.save()

    messages.warning(
        request,
        f"El estudiante {estudiante.nombres} ha sido desactivado."
    )

    return redirect("list_estudiantes")


@login_required
def reactivar_estudiante(request, pk):
    """
    Reactiva un estudiante previamente desactivado.

    Cambia el campo estado a True y luego vuelve al listado
    de estudiantes inactivos.
    """

    estudiante = get_object_or_404(Estudiante, pk=pk)

    estudiante.estado = True
    estudiante.save()

    messages.success(
        request,
        f"El estudiante {estudiante.nombres} ha sido reactivado."
    )

    return redirect("/estudiantes/?inactivos=on")


@login_required
def eliminar_estudiante_fisico(request, pk):
    """
    Elimina definitivamente un estudiante de la base de datos.

    Reglas:
    - No se puede eliminar si tiene inscripciones históricas.
    - Si el estudiante tiene tutor asociado, se revisa si ese tutor tiene otros estudiantes.
    - Si el tutor tiene otros estudiantes, no se elimina.
    - Si el tutor solo estaba asociado a ese estudiante, también se elimina.

    Esta vista debe usarse con mucho cuidado porque borra datos reales.
    """

    estudiante = get_object_or_404(Estudiante, pk=pk)

    # No permite eliminar estudiantes con historial de inscripción.
    if estudiante.inscripcion_set.exists():
        messages.error(
            request,
            "Error de seguridad: El estudiante tiene inscripciones históricas."
        )

        return redirect("/estudiantes/?inactivos=on")

    # Busca la primera relación de parentesco del estudiante.
    relacion = estudiante.parentesco_set.first()

    if relacion:
        tutor = relacion.tutor

        # Verifica si el tutor tiene otros estudiantes asociados.
        otros_hijos = (
            tutor.parentesco_set
            .exclude(estudiante=estudiante)
            .count()
        )

        if otros_hijos > 0:
            messages.error(
                request,
                "Error: No se puede eliminar. "
                "El tutor tiene otros estudiantes asociados."
            )

            return redirect("/estudiantes/?inactivos=on")

        else:
            # Si el tutor no tiene otros estudiantes, también se elimina.
            tutor.delete()

    nombre = f"{estudiante.nombres} {estudiante.apellido_paterno}"

    # Eliminación física del estudiante.
    estudiante.delete()

    messages.success(
        request,
        f"¡Completado! El estudiante {nombre} y su tutor han sido eliminados "
        f"de la base de datos."
    )

    return redirect("/estudiantes/?inactivos=on")
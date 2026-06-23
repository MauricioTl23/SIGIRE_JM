from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from academic.models import Gestion, Paralelo
from students.models import Estudiante

from .models import EntregaDocumento, Inscripcion, Requisito


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_siguiente_paralelo(paralelo_actual):
    """
    Obtiene el paralelo correspondiente al siguiente curso académico.

    Esta función se usa principalmente para reinscripciones de estudiantes
    con inscripción previa.

    Ejemplo:
    - Primero de Primaria A -> Segundo de Primaria A
    - Sexto de Primaria A -> Primero de Secundaria A

    Si no encuentra el mismo paralelo con la misma letra, busca el primer
    paralelo activo disponible del siguiente curso.
    """

    nivel_actual = paralelo_actual.grado.nivel.nombre.lower()
    grado_actual = paralelo_actual.grado.nombre.lower()
    letra_actual = paralelo_actual.letra

    # Secuencia académica institucional.
    secuencia = [
        ("primaria", "primero"),
        ("primaria", "segundo"),
        ("primaria", "tercero"),
        ("primaria", "cuarto"),
        ("primaria", "quinto"),
        ("primaria", "sexto"),
        ("secundaria", "primero"),
        ("secundaria", "segundo"),
        ("secundaria", "tercero"),
        ("secundaria", "cuarto"),
        ("secundaria", "quinto"),
        ("secundaria", "sexto"),
    ]

    posicion_actual = None

    # Busca la posición actual del estudiante dentro de la secuencia académica.
    for index, (nivel, grado) in enumerate(secuencia):
        if nivel in nivel_actual and grado in grado_actual:
            posicion_actual = index
            break

    # Si no se encuentra el grado actual en la secuencia, no se puede promover.
    if posicion_actual is None:
        return None

    # Si ya está en el último curso, no existe curso superior.
    if posicion_actual + 1 >= len(secuencia):
        return None

    siguiente_nivel, siguiente_grado = secuencia[posicion_actual + 1]

    # Primero intenta encontrar el siguiente curso con la misma letra de paralelo.
    siguiente_paralelo = Paralelo.objects.filter(
        estado=True,
        letra=letra_actual,
        grado__nombre__icontains=siguiente_grado,
        grado__nivel__nombre__icontains=siguiente_nivel,
    ).first()

    if siguiente_paralelo:
        return siguiente_paralelo

    # Si no existe la misma letra, toma el primer paralelo activo disponible.
    return Paralelo.objects.filter(
        estado=True,
        grado__nombre__icontains=siguiente_grado,
        grado__nivel__nombre__icontains=siguiente_nivel,
    ).first()


def calcular_edad(fecha_nacimiento, fecha_referencia):
    """
    Calcula la edad exacta de un estudiante usando una fecha de referencia.

    Se usa para sugerir el curso correspondiente cuando el estudiante
    no tiene inscripción previa.
    """

    edad = fecha_referencia.year - fecha_nacimiento.year

    # Si todavía no cumplió años en el año actual, se resta un año.
    if (fecha_referencia.month, fecha_referencia.day) < (
        fecha_nacimiento.month,
        fecha_nacimiento.day
    ):
        edad -= 1

    return edad


def generar_rude_institucional(gestion_actual):
    """
    Genera un código RUDE institucional automático.

    Formato:
    - Código de unidad educativa + año de gestión + correlativo.

    Ejemplo:
    385075020260001

    Nota:
    El correlativo se calcula según la cantidad de inscripciones existentes
    en la gestión actual.
    """

    codigo_unidad = "3850750"

    correlativo = (
        Inscripcion.objects
        .filter(gestion=gestion_actual)
        .count() + 1
    )

    return f"{codigo_unidad}{gestion_actual.anio}{correlativo:04d}"


def obtener_requisitos_para_inscripcion(tipo_inscripcion):
    """
    Devuelve los requisitos documentales según el tipo de inscripción.

    Si el estudiante tiene inscripción previa, solo se solicitan documentos
    específicos como libreta y RUDE.

    Si el estudiante no tiene inscripción previa, se solicitan todos los
    requisitos activos.
    """

    if tipo_inscripcion == "con_previa":
        return (
            Requisito.objects
            .filter(estado=True)
            .filter(
                Q(nombre_documento__icontains="libreta")
                | Q(nombre_documento__iexact="RUDE")
            )
            .order_by("id")
        )

    return Requisito.objects.filter(
        estado=True
    ).order_by(
        "id"
    )


def obtener_paralelo_por_edad(estudiante):
    """
    Sugiere un paralelo según la edad del estudiante.

    Se usa para estudiantes nuevos, es decir, estudiantes sin inscripción previa.

    Mapa de edad:
    - 6 años  -> Primero de Primaria
    - 7 años  -> Segundo de Primaria
    - 8 años  -> Tercero de Primaria
    - 9 años  -> Cuarto de Primaria
    - 10 años -> Quinto de Primaria
    - 11 años -> Sexto de Primaria
    - 12 años -> Primero de Secundaria
    - 13 años -> Segundo de Secundaria
    - 14 años -> Tercero de Secundaria
    - 15 años -> Cuarto de Secundaria
    - 16 años -> Quinto de Secundaria
    - 17/18 años -> Sexto de Secundaria
    """

    hoy = timezone.now().date()
    edad = calcular_edad(estudiante.fecha_nacimiento, hoy)

    mapa_edad_curso = {
        6: ("primaria", "primero"),
        7: ("primaria", "segundo"),
        8: ("primaria", "tercero"),
        9: ("primaria", "cuarto"),
        10: ("primaria", "quinto"),
        11: ("primaria", "sexto"),
        12: ("secundaria", "primero"),
        13: ("secundaria", "segundo"),
        14: ("secundaria", "tercero"),
        15: ("secundaria", "cuarto"),
        16: ("secundaria", "quinto"),
        17: ("secundaria", "sexto"),
        18: ("secundaria", "sexto"),
    }

    curso_esperado = mapa_edad_curso.get(edad)

    # Si la edad no está dentro del mapa, no se puede sugerir curso automático.
    if not curso_esperado:
        return None, edad

    nivel, grado = curso_esperado

    # Busca el primer paralelo activo que coincida con el curso esperado.
    paralelo_sugerido = (
        Paralelo.objects
        .filter(
            estado=True,
            grado__nivel__nombre__icontains=nivel,
            grado__nombre__icontains=grado
        )
        .order_by("letra")
        .first()
    )

    return paralelo_sugerido, edad


# ============================================================
# REGISTRO DE INSCRIPCIÓN
# ============================================================

@login_required
def registrar_inscripcion_view(request):
    """
    Registra una inscripción nueva o muestra el formulario de inscripción.

    Esta vista maneja dos escenarios:

    GET:
    - Muestra el formulario de inscripción.
    - Sugiere paralelo según edad o inscripción previa.
    - Sugiere RUDE si el estudiante ya tenía uno anterior.
    - Carga requisitos documentales.

    POST:
    - Valida estudiante, gestión activa, paralelo, RUDE y documentos.
    - Crea la inscripción.
    - Crea las entregas documentales.
    - Define si la documentación queda completa o pendiente.

    Template:
    - Inscriptions/form_enrollment.html
    """

    # ========================================================
    # PROCESAMIENTO POST: GUARDAR INSCRIPCIÓN
    # ========================================================

    if request.method == "POST":
        estudiante_id = request.POST.get("estudiante_id")
        paralelo_id = request.POST.get("paralelo")
        tipo_inscripcion = request.POST.get("tipo_inscripcion", "")
        tipo_rude = request.POST.get("tipo_rude", "manual")
        rude_manual = request.POST.get("rude", "").strip()
        observacion = request.POST.get("observacion", "")
        requisitos_entregados = request.POST.getlist("requisitos")

        # Busca al estudiante que será inscrito.
        estudiante = get_object_or_404(
            Estudiante,
            cedula_identidad=estudiante_id
        )

        # Obtiene la gestión activa actual.
        gestion_actual = (
            Gestion.objects
            .filter(estado=True)
            .order_by("-anio")
            .first()
        )

        if not gestion_actual:
            messages.error(
                request,
                "No existe una gestión activa para realizar inscripciones."
            )
            return redirect("estructura_academica")

        # ====================================================
        # DETERMINACIÓN DEL PARALELO
        # ====================================================

        if tipo_inscripcion == "con_previa":
            aprobo_anterior = request.POST.get("aprobo_anterior") == "on"

            ultima_inscripcion_estudiante = (
                Inscripcion.objects
                .filter(estudiante=estudiante)
                .select_related(
                    "paralelo",
                    "paralelo__grado",
                    "paralelo__grado__nivel",
                    "gestion"
                )
                .order_by("-gestion__anio")
                .first()
            )

            if not ultima_inscripcion_estudiante:
                messages.error(
                    request,
                    "No se encontró inscripción previa para este estudiante."
                )
                return redirect("list_estudiantes")

            # Si aprobó, se intenta promover al siguiente curso.
            if aprobo_anterior:
                paralelo = obtener_siguiente_paralelo(
                    ultima_inscripcion_estudiante.paralelo
                )

                # Si no existe curso superior, se mantiene en el mismo paralelo.
                if not paralelo:
                    paralelo = ultima_inscripcion_estudiante.paralelo

            # Si no aprobó, repite el mismo curso.
            else:
                paralelo = ultima_inscripcion_estudiante.paralelo

        else:
            # Para estudiantes nuevos, se usa el paralelo seleccionado.
            paralelo = get_object_or_404(
                Paralelo,
                pk=paralelo_id
            )

        # ====================================================
        # VALIDACIÓN DE INSCRIPCIÓN DUPLICADA
        # ====================================================

        ya_inscrito = Inscripcion.objects.filter(
            estudiante=estudiante,
            gestion=gestion_actual
        ).exists()

        if ya_inscrito:
            messages.error(
                request,
                f"El estudiante {estudiante.nombres} ya tiene una inscripción "
                f"en la gestión {gestion_actual.anio}."
            )
            return redirect("list_estudiantes")

        # ====================================================
        # DETERMINACIÓN DEL RUDE
        # ====================================================

        ultima_inscripcion_estudiante = (
            Inscripcion.objects
            .filter(estudiante=estudiante)
            .order_by("-gestion__anio")
            .first()
        )

        # Si el estudiante ya tenía inscripción, conserva su RUDE.
        if ultima_inscripcion_estudiante:
            rude = ultima_inscripcion_estudiante.rude

        # Si es nuevo y eligió RUDE automático, se genera uno institucional.
        elif tipo_rude == "auto":
            rude = generar_rude_institucional(gestion_actual)

        # Si eligió RUDE manual, se toma el ingresado.
        else:
            rude = rude_manual

        if not rude:
            messages.error(
                request,
                "Debe ingresar o generar un código RUDE."
            )
            return redirect("registrar_inscripcion_view")

        # Evita que el mismo RUDE pertenezca a otro estudiante.
        rude_en_otro_estudiante = (
            Inscripcion.objects
            .filter(rude=rude)
            .exclude(estudiante=estudiante)
            .exists()
        )

        if rude_en_otro_estudiante:
            messages.error(
                request,
                f"El RUDE {rude} ya está asignado a otro estudiante."
            )
            return redirect("list_estudiantes")

        # Obtiene los requisitos según el tipo de inscripción.
        requisitos = obtener_requisitos_para_inscripcion(tipo_inscripcion)

        # ====================================================
        # CREACIÓN DE INSCRIPCIÓN Y DOCUMENTOS
        # ====================================================

        with transaction.atomic():
            # Crea la inscripción principal.
            inscripcion = Inscripcion.objects.create(
                estudiante=estudiante,
                paralelo=paralelo,
                usuario=request.user,
                gestion=gestion_actual,
                estado=True,
                rude=rude,
                observacion=observacion,
            )

            # Crea una entrega documental por cada requisito.
            for requisito in requisitos:
                entregado = str(requisito.id) in requisitos_entregados

                EntregaDocumento.objects.create(
                    inscripcion=inscripcion,
                    requisito=requisito,
                    estado=entregado,
                    fecha_entrega=timezone.now().date() if entregado else None,
                )

            # Verifica si faltan documentos obligatorios.
            faltan_documentos = EntregaDocumento.objects.filter(
                inscripcion=inscripcion,
                requisito__obligatorio=True,
                estado=False
            ).exists()

            if faltan_documentos:
                inscripcion.estado_documental = "pendiente"
                inscripcion.fecha_limite_documentos = (
                    timezone.now().date() + timedelta(days=30)
                )

                mensaje = (
                    f"Inscripción registrada como pendiente. "
                    f"El tutor tiene plazo hasta "
                    f"{inscripcion.fecha_limite_documentos} "
                    f"para completar documentos."
                )

            else:
                inscripcion.estado_documental = "completa"
                inscripcion.fecha_limite_documentos = None

                mensaje = (
                    "Inscripción registrada correctamente con documentación completa."
                )

            inscripcion.save()

        messages.success(request, mensaje)

        return redirect("list_inscripciones")

    # ========================================================
    # PROCESAMIENTO GET: MOSTRAR FORMULARIO
    # ========================================================

    estudiante_id = request.GET.get("estudiante_id")
    tipo_inscripcion = request.GET.get("tipo_inscripcion", "")

    estudiante = None
    ultima_inscripcion = None
    paralelo_anterior = None
    paralelo_sugerido = None
    paralelo_si_aprueba = None
    paralelo_si_repite = None
    mensaje_sugerencia = None
    rude_sugerido = None
    rude_bloqueado = False

    gestion_actual = (
        Gestion.objects
        .filter(estado=True)
        .order_by("-anio")
        .first()
    )

    if not gestion_actual:
        messages.error(
            request,
            "No existe una gestión activa para realizar inscripciones."
        )
        return redirect("estructura_academica")

    # Busca la gestión anterior a la actual.
    gestion_pasada = (
        Gestion.objects
        .filter(anio__lt=gestion_actual.anio)
        .order_by("-anio")
        .first()
    )

    if estudiante_id:
        estudiante = get_object_or_404(
            Estudiante,
            cedula_identidad=estudiante_id
        )

        # Si ya tenía inscripción anterior, se sugiere conservar su RUDE.
        ultima_inscripcion_rude = (
            Inscripcion.objects
            .filter(estudiante=estudiante)
            .order_by("-gestion__anio")
            .first()
        )

        if ultima_inscripcion_rude:
            rude_sugerido = ultima_inscripcion_rude.rude
            rude_bloqueado = True

        # Busca inscripción de la gestión pasada.
        if gestion_pasada:
            ultima_inscripcion = (
                Inscripcion.objects
                .filter(
                    estudiante=estudiante,
                    gestion=gestion_pasada
                )
                .select_related(
                    "gestion",
                    "paralelo",
                    "paralelo__grado",
                    "paralelo__grado__nivel"
                )
                .first()
            )

        # Si tiene inscripción previa, se sugieren opciones de promoción.
        if ultima_inscripcion:
            paralelo_anterior = ultima_inscripcion.paralelo
            paralelo_si_repite = paralelo_anterior

            paralelo_siguiente = obtener_siguiente_paralelo(paralelo_anterior)

            if paralelo_siguiente:
                paralelo_si_aprueba = paralelo_siguiente
                paralelo_sugerido = paralelo_siguiente

                mensaje_sugerencia = (
                    f"Gestión pasada: {paralelo_anterior.grado.nombre} de "
                    f"{paralelo_anterior.grado.nivel.nombre} "
                    f"{paralelo_anterior.letra}. "
                    f"Si aprobó, le corresponde: "
                    f"{paralelo_si_aprueba.grado.nombre} de "
                    f"{paralelo_si_aprueba.grado.nivel.nombre} "
                    f"{paralelo_si_aprueba.letra}. "
                    f"Si no aprobó, debe repetir el mismo curso."
                )

            else:
                paralelo_si_aprueba = paralelo_anterior
                paralelo_sugerido = paralelo_anterior

                mensaje_sugerencia = (
                    f"Gestión pasada: {paralelo_anterior.grado.nombre} de "
                    f"{paralelo_anterior.grado.nivel.nombre} "
                    f"{paralelo_anterior.letra}. "
                    f"No existe curso superior; si corresponde, debe "
                    f"reinscribirse en el mismo curso."
                )

        # Si no tiene inscripción previa, se sugiere curso por edad.
        if not ultima_inscripcion and tipo_inscripcion == "sin_previa":
            paralelo_por_edad, edad_estudiante = obtener_paralelo_por_edad(
                estudiante
            )

            if paralelo_por_edad:
                paralelo_sugerido = paralelo_por_edad

                mensaje_sugerencia = (
                    f"Según la edad del estudiante ({edad_estudiante} años), "
                    f"se sugiere inscribirlo en "
                    f"{paralelo_sugerido.grado.nombre} de "
                    f"{paralelo_sugerido.grado.nivel.nombre} "
                    f"{paralelo_sugerido.letra}."
                )

            else:
                mensaje_sugerencia = (
                    "La edad del estudiante no coincide con un curso automático. "
                    "Seleccione el paralelo manualmente."
                )

    # Lista de paralelos disponibles.
    paralelos = (
        Paralelo.objects
        .filter(estado=True)
        .select_related("grado", "grado__nivel")
        .order_by(
            "grado__nivel__nombre",
            "grado__nombre",
            "letra"
        )
    )

    # Lista de requisitos según el tipo de inscripción.
    requisitos = obtener_requisitos_para_inscripcion(tipo_inscripcion)

    context = {
        "gestion_actual": gestion_actual,
        "gestion_pasada": gestion_pasada,
        "estudiante": estudiante,
        "tipo_inscripcion": tipo_inscripcion,
        "ultima_inscripcion": ultima_inscripcion,
        "paralelo_anterior": paralelo_anterior,
        "paralelo_sugerido": paralelo_sugerido,
        "mensaje_sugerencia": mensaje_sugerencia,
        "paralelos": paralelos,
        "requisitos": requisitos,
        "rude_sugerido": rude_sugerido,
        "rude_bloqueado": rude_bloqueado,
        "paralelo_si_aprueba": paralelo_si_aprueba,
        "paralelo_si_repite": paralelo_si_repite,
    }

    return render(
        request,
        "Inscriptions/form_enrollment.html",
        context
    )


# ============================================================
# LISTADO, DETALLE E IMPRESIÓN DE INSCRIPCIONES
# ============================================================

@login_required
def list_inscripciones(request):
    """
    Lista las inscripciones activas de la gestión actual.

    Funcionalidades:
    - Buscar por nombre, apellidos, C.I. o RUDE.
    - Filtrar por paralelo.
    - Filtrar por estado documental.
    - Mostrar solo inscripciones activas.
    - Mostrar, por defecto, solo la gestión activa.

    Template:
    - Inscriptions/list_of_subscribers.html
    """

    query = request.GET.get("search", "").strip()
    paralelo_id = request.GET.get("paralelo", "")
    estado_documental = request.GET.get("estado_documental", "")

    inscripciones = (
        Inscripcion.objects
        .select_related(
            "estudiante",
            "gestion",
            "paralelo",
            "paralelo__grado",
            "paralelo__grado__nivel",
        )
        .prefetch_related(
            "estudiante__parentesco_set",
            "estudiante__parentesco_set__tutor",
        )
        .filter(estado=True)
        .order_by(
            "-fecha_registro",
            "estudiante__apellido_paterno"
        )
    )

    gestion_actual = (
        Gestion.objects
        .filter(estado=True)
        .order_by("-anio")
        .first()
    )

    # Si existe gestión activa, se muestran solo sus inscripciones.
    if gestion_actual:
        inscripciones = inscripciones.filter(gestion=gestion_actual)

    # Filtro de búsqueda.
    if query:
        inscripciones = inscripciones.filter(
            Q(estudiante__nombres__icontains=query)
            | Q(estudiante__apellido_paterno__icontains=query)
            | Q(estudiante__apellido_materno__icontains=query)
            | Q(estudiante__cedula_identidad__icontains=query)
            | Q(rude__icontains=query)
        ).distinct()

    # Filtro por paralelo.
    if paralelo_id:
        inscripciones = inscripciones.filter(paralelo_id=paralelo_id)

    # Filtro por estado documental.
    if estado_documental:
        inscripciones = inscripciones.filter(
            estado_documental=estado_documental
        )

    # Lista de paralelos para el filtro.
    paralelos = (
        Paralelo.objects
        .filter(estado=True)
        .select_related("grado", "grado__nivel")
        .order_by(
            "grado__nivel__nombre",
            "grado__nombre",
            "letra"
        )
    )

    context = {
        "inscripciones": inscripciones,
        "paralelos": paralelos,
        "gestion_actual": gestion_actual,
        "search_query": query,
        "paralelo_filter": paralelo_id,
        "estado_documental_filter": estado_documental,
    }

    return render(
        request,
        "Inscriptions/list_of_subscribers.html",
        context
    )


@login_required
def detalle_inscripcion(request, pk):
    """
    Muestra el detalle completo de una inscripción.

    Incluye:
    - Datos del estudiante.
    - Datos de gestión.
    - Paralelo.
    - Usuario que registró.
    - Tutor o tutores relacionados.
    - Documentos entregados o pendientes.

    Template:
    - Inscriptions/detail_enrollment.html
    """

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            "estudiante",
            "gestion",
            "paralelo",
            "paralelo__grado",
            "paralelo__grado__nivel",
            "usuario",
        ).prefetch_related(
            "estudiante__parentesco_set",
            "estudiante__parentesco_set__tutor",
        ),
        pk=pk
    )

    entregas = (
        EntregaDocumento.objects
        .filter(inscripcion=inscripcion)
        .select_related("requisito")
        .order_by("requisito__id")
    )

    return render(
        request,
        "Inscriptions/detail_enrollment.html",
        {
            "inscripcion": inscripcion,
            "entregas": entregas,
        }
    )


@login_required
def imprimir_inscripcion(request, pk):
    """
    Muestra la versión imprimible de una inscripción.

    Esta vista sirve para generar o imprimir la ficha de inscripción.

    Template:
    - Inscriptions/print_enrollment.html
    """

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            "estudiante",
            "gestion",
            "paralelo",
            "paralelo__grado",
            "paralelo__grado__nivel",
            "usuario",
        ).prefetch_related(
            "estudiante__parentesco_set",
            "estudiante__parentesco_set__tutor",
        ),
        pk=pk
    )

    entregas = (
        EntregaDocumento.objects
        .filter(inscripcion=inscripcion)
        .select_related("requisito")
        .order_by("requisito__id")
    )

    return render(
        request,
        "Inscriptions/print_enrollment.html",
        {
            "inscripcion": inscripcion,
            "entregas": entregas,
        }
    )


# ============================================================
# DOCUMENTOS DE INSCRIPCIÓN
# ============================================================

@login_required
def completar_documentos(request, pk):
    """
    Permite actualizar documentos entregados de una inscripción.

    Esta versión consolida las dos funciones duplicadas del archivo original.

    Comportamiento:
    - Marca como entregados los documentos seleccionados.
    - Marca como pendientes los documentos no seleccionados.
    - Asigna fecha de entrega cuando un documento se marca como entregado.
    - Borra fecha de entrega cuando un documento vuelve a pendiente.
    - Actualiza el estado documental de la inscripción.

    Template:
    - Inscriptions/completar_documentos.html
    """

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            "estudiante",
            "gestion",
            "paralelo",
            "paralelo__grado",
            "paralelo__grado__nivel"
        ),
        pk=pk
    )

    entregas = (
        EntregaDocumento.objects
        .filter(inscripcion=inscripcion)
        .select_related("requisito")
        .order_by("requisito__id")
    )

    if request.method == "POST":
        documentos_entregados = request.POST.getlist("documentos")

        # Convierte los IDs recibidos en enteros válidos.
        documentos_entregados_ids = set()

        for doc_id in documentos_entregados:
            try:
                documentos_entregados_ids.add(int(doc_id))
            except ValueError:
                continue

        # Actualiza cada documento según si fue marcado o no.
        for entrega in entregas:
            fue_entregado = entrega.id in documentos_entregados_ids

            entrega.estado = fue_entregado

            if fue_entregado:
                if not entrega.fecha_entrega:
                    entrega.fecha_entrega = timezone.now().date()
            else:
                entrega.fecha_entrega = None

            entrega.save()

        # Verifica si todavía faltan documentos obligatorios.
        faltan_obligatorios = EntregaDocumento.objects.filter(
            inscripcion=inscripcion,
            requisito__obligatorio=True,
            estado=False
        ).exists()

        if faltan_obligatorios:
            inscripcion.estado_documental = "pendiente"

            # Si no tenía fecha límite, se le da nuevamente 30 días.
            if not inscripcion.fecha_limite_documentos:
                inscripcion.fecha_limite_documentos = (
                    timezone.now().date() + timedelta(days=30)
                )

        else:
            inscripcion.estado_documental = "completa"
            inscripcion.fecha_limite_documentos = None

        inscripcion.save()

        messages.success(
            request,
            "Documentos actualizados correctamente."
        )

        return redirect("list_inscripciones")

    return render(
        request,
        "Inscriptions/completar_documentos.html",
        {
            "inscripcion": inscripcion,
            "entregas": entregas,
        }
    )


# ============================================================
# GESTIÓN DE REQUISITOS
# ============================================================

@login_required
@require_POST
def crear_requisito(request):
    """
    Crea un nuevo requisito documental.

    Ejemplos:
    - Certificado de nacimiento.
    - Fotocopia de C.I.
    - Libreta escolar.
    - RUDE.

    Esta vista recibe datos por POST desde la pantalla de estructura académica.
    """

    nombre = request.POST.get("nombre_documento")
    obligatorio = request.POST.get("obligatorio") == "on"

    if nombre:
        Requisito.objects.create(
            nombre_documento=nombre,
            obligatorio=obligatorio
        )

        messages.success(
            request,
            f"Requisito '{nombre}' registrado correctamente."
        )

    else:
        messages.error(
            request,
            "El nombre del documento no puede estar vacío."
        )

    return redirect("estructura_academica")


@login_required
def eliminar_requisito(request, pk):
    """
    Elimina o desactiva un requisito documental.

    Regla:
    - Si el requisito ya fue usado en entregas documentales, no se elimina
      físicamente; solo se desactiva.
    - Si nunca fue usado, se elimina definitivamente.
    """

    requisito = get_object_or_404(Requisito, pk=pk)
    nombre = requisito.nombre_documento

    existe_en_entregas = EntregaDocumento.objects.filter(
        requisito=requisito
    ).exists()

    if existe_en_entregas:
        requisito.estado = False
        requisito.save()

        messages.warning(
            request,
            f"El requisito '{nombre}' se ha desactivado "
            f"(no se eliminó físicamente por integridad de datos)."
        )

    else:
        requisito.delete()

        messages.success(
            request,
            f"Requisito '{nombre}' eliminado físicamente con éxito."
        )

    return redirect("estructura_academica")


@login_required
def editar_requisito(request, pk):
    """
    Edita un requisito documental existente.

    Permite modificar:
    - Nombre del documento.
    - Si es obligatorio u opcional.

    Template:
    - Inscriptions/edit_requirement.html
    """

    requisito = get_object_or_404(Requisito, pk=pk)

    if request.method == "POST":
        nuevo_nombre = request.POST.get(
            "nombre_documento",
            ""
        ).strip()

        obligatorio = request.POST.get("obligatorio") == "on"

        if not nuevo_nombre:
            messages.error(
                request,
                "El nombre del documento no puede estar vacío."
            )
            return redirect("estructura_academica")

        if (
            requisito.nombre_documento == nuevo_nombre
            and requisito.obligatorio == obligatorio
        ):
            messages.info(
                request,
                "No se detectaron cambios en el requisito."
            )
            return redirect("estructura_academica")

        requisito.nombre_documento = nuevo_nombre
        requisito.obligatorio = obligatorio
        requisito.save()

        messages.success(
            request,
            "Requisito actualizado correctamente."
        )

        return redirect("estructura_academica")

    return render(
        request,
        "Inscriptions/edit_requirement.html",
        {
            "requisito": requisito,
        }
    )
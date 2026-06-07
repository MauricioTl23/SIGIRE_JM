from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from .models import Inscripcion, Requisito, EntregaDocumento
from students.models import Estudiante
from academic.models import Gestion, Paralelo

def obtener_siguiente_paralelo(paralelo_actual):
    nivel_actual = paralelo_actual.grado.nivel.nombre.lower()
    grado_actual = paralelo_actual.grado.nombre.lower()
    letra_actual = paralelo_actual.letra

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

    for index, (nivel, grado) in enumerate(secuencia):
        if nivel in nivel_actual and grado in grado_actual:
            posicion_actual = index
            break

    if posicion_actual is None:
        return None

    if posicion_actual + 1 >= len(secuencia):
        return None

    siguiente_nivel, siguiente_grado = secuencia[posicion_actual + 1]

    siguiente_paralelo = Paralelo.objects.filter(
        estado=True,
        letra=letra_actual,
        grado__nombre__icontains=siguiente_grado,
        grado__nivel__nombre__icontains=siguiente_nivel,
    ).first()

    if siguiente_paralelo:
        return siguiente_paralelo

    return Paralelo.objects.filter(
        estado=True,
        grado__nombre__icontains=siguiente_grado,
        grado__nivel__nombre__icontains=siguiente_nivel,
    ).first()
    
def calcular_edad(fecha_nacimiento, fecha_referencia):
    edad = fecha_referencia.year - fecha_nacimiento.year

    if (fecha_referencia.month, fecha_referencia.day) < (
        fecha_nacimiento.month,
        fecha_nacimiento.day
    ):
        edad -= 1

    return edad

def generar_rude_institucional(gestion_actual):
    codigo_unidad = "3850750"

    correlativo = (
        Inscripcion.objects
        .filter(gestion=gestion_actual)
        .count() + 1
    )

    return f"{codigo_unidad}{gestion_actual.anio}{correlativo:04d}"

def obtener_requisitos_para_inscripcion(tipo_inscripcion):
    if tipo_inscripcion == "con_previa":
        return (
            Requisito.objects
            .filter(estado=True)
            .filter(
                Q(nombre_documento__icontains="libreta") |
                Q(nombre_documento__iexact="RUDE")
            )
            .order_by("id")
        )

    return Requisito.objects.filter(estado=True).order_by("id")

def obtener_paralelo_por_edad(estudiante):
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

    if not curso_esperado:
        return None, edad

    nivel, grado = curso_esperado

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
    
@login_required
def registrar_inscripcion_view(request):
    if request.method == "POST":
        estudiante_id = request.POST.get("estudiante_id")
        paralelo_id = request.POST.get("paralelo")
        tipo_inscripcion = request.POST.get("tipo_inscripcion", "")
        tipo_rude = request.POST.get("tipo_rude", "manual")
        rude_manual = request.POST.get("rude", "").strip()
        observacion = request.POST.get("observacion", "")
        requisitos_entregados = request.POST.getlist("requisitos")

        estudiante = get_object_or_404(
            Estudiante,
            cedula_identidad=estudiante_id
        )

        gestion_actual = Gestion.objects.filter(
            estado=True
        ).order_by("-anio").first()
        
        if tipo_inscripcion == "con_previa":
            aprobo_anterior = request.POST.get("aprobo_anterior") == "on"

            ultima_inscripcion_estudiante = (
                Inscripcion.objects
                .filter(estudiante=estudiante)
                .select_related("paralelo", "paralelo__grado", "paralelo__grado__nivel", "gestion")
                .order_by("-gestion__anio")
                .first()
            )

            if not ultima_inscripcion_estudiante:
                messages.error(request, "No se encontró inscripción previa para este estudiante.")
                return redirect("list_estudiantes")

            if aprobo_anterior:
                paralelo = obtener_siguiente_paralelo(ultima_inscripcion_estudiante.paralelo)

                if not paralelo:
                    paralelo = ultima_inscripcion_estudiante.paralelo
            else:
                paralelo = ultima_inscripcion_estudiante.paralelo

        else:
            paralelo = get_object_or_404(
                Paralelo,
                pk=paralelo_id
            )

        if not gestion_actual:
            messages.error(request, "No existe una gestión activa para realizar inscripciones.")
            return redirect("estructura_academica")

        ya_inscrito = Inscripcion.objects.filter(
            estudiante=estudiante,
            gestion=gestion_actual
        ).exists()

        if ya_inscrito:
            messages.error(
                request,
                f"El estudiante {estudiante.nombres} ya tiene una inscripción en la gestión {gestion_actual.anio}."
            )
            return redirect("list_estudiantes")

        ultima_inscripcion_estudiante = (
            Inscripcion.objects
            .filter(estudiante=estudiante)
            .order_by("-gestion__anio")
            .first()
        )

        if ultima_inscripcion_estudiante:
            rude = ultima_inscripcion_estudiante.rude

        elif tipo_rude == "auto":
            rude = generar_rude_institucional(gestion_actual)

        else:
            rude = rude_manual

        if not rude:
            messages.error(request, "Debe ingresar o generar un código RUDE.")
            return redirect("registrar_inscripcion_view")

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

        requisitos = obtener_requisitos_para_inscripcion(tipo_inscripcion)

        with transaction.atomic():
            inscripcion = Inscripcion.objects.create(
                estudiante=estudiante,
                paralelo=paralelo,
                usuario=request.user,
                gestion=gestion_actual,
                estado=True,
                rude=rude,
                observacion=observacion,
            )

            for requisito in requisitos:
                entregado = str(requisito.id) in requisitos_entregados

                EntregaDocumento.objects.create(
                    inscripcion=inscripcion,
                    requisito=requisito,
                    estado=entregado,
                    fecha_entrega=timezone.now().date() if entregado else None,
                )

            faltan_documentos = EntregaDocumento.objects.filter(
                inscripcion=inscripcion,
                requisito__obligatorio=True,
                estado=False
            ).exists()

            if faltan_documentos:
                inscripcion.estado_documental = "pendiente"
                inscripcion.fecha_limite_documentos = timezone.now().date() + timedelta(days=30)
                mensaje = (
                    f"Inscripción registrada como pendiente. "
                    f"El tutor tiene plazo hasta {inscripcion.fecha_limite_documentos} para completar documentos."
                )
            else:
                inscripcion.estado_documental = "completa"
                inscripcion.fecha_limite_documentos = None
                mensaje = "Inscripción registrada correctamente con documentación completa."

            inscripcion.save()

        messages.success(request, mensaje)
        return redirect("list_inscripciones")

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

    gestion_actual = Gestion.objects.filter(estado=True).order_by("-anio").first()

    if not gestion_actual:
        messages.error(request, "No existe una gestión activa para realizar inscripciones.")
        return redirect("estructura_academica")

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

        ultima_inscripcion_rude = (
            Inscripcion.objects
            .filter(estudiante=estudiante)
            .order_by("-gestion__anio")
            .first()
        )

        if ultima_inscripcion_rude:
            rude_sugerido = ultima_inscripcion_rude.rude
            rude_bloqueado = True

        if gestion_pasada:
            ultima_inscripcion = (
                Inscripcion.objects
                .filter(estudiante=estudiante, gestion=gestion_pasada)
                .select_related(
                    "gestion",
                    "paralelo",
                    "paralelo__grado",
                    "paralelo__grado__nivel"
                )
                .first()
            )

        if ultima_inscripcion:
            paralelo_anterior = ultima_inscripcion.paralelo
            paralelo_si_repite = paralelo_anterior

            paralelo_siguiente = obtener_siguiente_paralelo(paralelo_anterior)

            if paralelo_siguiente:
                paralelo_si_aprueba = paralelo_siguiente
                paralelo_sugerido = paralelo_siguiente
                mensaje_sugerencia = (
                    f"Gestión pasada: {paralelo_anterior.grado.nombre} de "
                    f"{paralelo_anterior.grado.nivel.nombre} {paralelo_anterior.letra}. "
                    f"Si aprobó, le corresponde: "
                    f"{paralelo_si_aprueba.grado.nombre} de "
                    f"{paralelo_si_aprueba.grado.nivel.nombre} {paralelo_si_aprueba.letra}. "
                    f"Si no aprobó, debe repetir el mismo curso."
                )
            else:
                paralelo_si_aprueba = paralelo_anterior
                paralelo_sugerido = paralelo_anterior
                mensaje_sugerencia = (
                    f"Gestión pasada: {paralelo_anterior.grado.nombre} de "
                    f"{paralelo_anterior.grado.nivel.nombre} {paralelo_anterior.letra}. "
                    f"No existe curso superior; si corresponde, debe reinscribirse en el mismo curso."
                )

        if not ultima_inscripcion and tipo_inscripcion == "sin_previa":
            paralelo_por_edad, edad_estudiante = obtener_paralelo_por_edad(estudiante)

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

    paralelos = (
        Paralelo.objects
        .filter(estado=True)
        .select_related("grado", "grado__nivel")
        .order_by("grado__nivel__nombre", "grado__nombre", "letra")
    )

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

    return render(request, "Inscriptions/form_enrollment.html", context)

@login_required
def list_inscripciones(request):
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
        .order_by("-fecha_registro", "estudiante__apellido_paterno")
    )

    gestion_actual = Gestion.objects.filter(estado=True).order_by("-anio").first()

    if gestion_actual:
        inscripciones = inscripciones.filter(gestion=gestion_actual)

    if query:
        inscripciones = inscripciones.filter(
            Q(estudiante__nombres__icontains=query) |
            Q(estudiante__apellido_paterno__icontains=query) |
            Q(estudiante__apellido_materno__icontains=query) |
            Q(estudiante__cedula_identidad__icontains=query) |
            Q(rude__icontains=query)
        ).distinct()

    if paralelo_id:
        inscripciones = inscripciones.filter(paralelo_id=paralelo_id)

    if estado_documental:
        inscripciones = inscripciones.filter(estado_documental=estado_documental)

    paralelos = (
        Paralelo.objects
        .filter(estado=True)
        .select_related("grado", "grado__nivel")
        .order_by("grado__nivel__nombre", "grado__nombre", "letra")
    )

    return render(request, "Inscriptions/list_of_subscribers.html", {
        "inscripciones": inscripciones,
        "paralelos": paralelos,
        "gestion_actual": gestion_actual,
        "search_query": query,
        "paralelo_filter": paralelo_id,
        "estado_documental_filter": estado_documental,
    })

@login_required
def completar_documentos(request, pk):
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

        obligatorios = entregas.filter(requisito__obligatorio=True)
        obligatorios_ids = set(obligatorios.values_list("id", flat=True))
        documentos_entregados_ids = set()

        for doc_id in documentos_entregados:
            try:
                documentos_entregados_ids.add(int(doc_id))
            except ValueError:
                continue

        if not obligatorios_ids.issubset(documentos_entregados_ids):
            messages.warning(
                request,
                "Debe marcar todos los documentos obligatorios antes de guardar."
            )
            return redirect("completar_documentos", pk=inscripcion.pk)

        for entrega in entregas:
            fue_entregado = entrega.id in documentos_entregados_ids

            entrega.estado = fue_entregado

            if fue_entregado:
                if not entrega.fecha_entrega:
                    entrega.fecha_entrega = timezone.now().date()
            else:
                entrega.fecha_entrega = None

            entrega.save()

        inscripcion.estado_documental = "completa"
        inscripcion.fecha_limite_documentos = None
        inscripcion.save()

        messages.success(request, "Documentación completada correctamente.")
        return redirect("list_inscripciones")

    return render(request, "Inscriptions/completar_documentos.html", {
        "inscripcion": inscripcion,
        "entregas": entregas,
    })
    
@require_POST
def crear_requisito(request):
    nombre = request.POST.get('nombre_documento')
    obligatorio = request.POST.get('obligatorio') == 'on'
    
    if nombre:
        Requisito.objects.create(
            nombre_documento=nombre,
            obligatorio=obligatorio
        )
        messages.success(request, f"Requisito '{nombre}' registrado correctamente.")
    else:
        messages.error(request, "El nombre del documento no puede estar vacío.")
        
    return redirect('estructura_academica')

def eliminar_requisito(request, pk):
    requisito = get_object_or_404(Requisito, pk=pk)
    nombre = requisito.nombre_documento
    
    existe_en_entregas = EntregaDocumento.objects.filter(requisito=requisito).exists()
    
    if existe_en_entregas:
        requisito.estado = False
        requisito.save()
        messages.warning(request, f"El requisito '{nombre}' se ha desactivado (no se eliminó físicamente por integridad de datos).")
    else:
        requisito.delete()
        messages.success(request, f"Requisito '{nombre}' eliminado físicamente con éxito.")
        
    return redirect('estructura_academica')

def editar_requisito(request, pk):
    requisito = get_object_or_404(Requisito, pk=pk)

    if request.method == "POST":
        nuevo_nombre = request.POST.get('nombre_documento', '').strip()
        obligatorio = request.POST.get('obligatorio') == 'on'

        if not nuevo_nombre:
            messages.error(request, "El nombre del documento no puede estar vacío.")
            return redirect('estructura_academica')

        if requisito.nombre_documento == nuevo_nombre and requisito.obligatorio == obligatorio:
            messages.info(request, "No se detectaron cambios en el requisito.")
            return redirect('estructura_academica')

        requisito.nombre_documento = nuevo_nombre
        requisito.obligatorio = obligatorio
        requisito.save()

        messages.success(request, "Requisito actualizado correctamente.")
        return redirect('estructura_academica')

    return render(request, 'Inscriptions/edit_requirement.html', {'requisito': requisito})

@login_required
def detalle_inscripcion(request, pk):
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

    return render(request, "Inscriptions/detail_enrollment.html", {
        "inscripcion": inscripcion,
        "entregas": entregas,
    })


@login_required
def completar_documentos(request, pk):
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

        for entrega in entregas:
            fue_entregado = str(entrega.id) in documentos_entregados

            if fue_entregado:
                entrega.estado = True

                if not entrega.fecha_entrega:
                    entrega.fecha_entrega = timezone.now().date()

                entrega.save()

        faltan_obligatorios = EntregaDocumento.objects.filter(
            inscripcion=inscripcion,
            requisito__obligatorio=True,
            estado=False
        ).exists()

        if faltan_obligatorios:
            inscripcion.estado_documental = "pendiente"
        else:
            inscripcion.estado_documental = "completa"
            inscripcion.fecha_limite_documentos = None

        inscripcion.save()

        messages.success(request, "Documentos actualizados correctamente.")
        return redirect("list_inscripciones")

    return render(request, "Inscriptions/completar_documentos.html", {
        "inscripcion": inscripcion,
        "entregas": entregas,
    })


@login_required
def imprimir_inscripcion(request, pk):
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

    return render(request, "Inscriptions/print_enrollment.html", {
        "inscripcion": inscripcion,
        "entregas": entregas,
    })
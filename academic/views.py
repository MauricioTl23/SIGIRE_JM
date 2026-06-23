from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import only_director
from enrollment.models import Inscripcion, Requisito

from .forms import GradoForm, NivelForm, ParaleloForm
from .models import Gestion, Grado, Nivel, Paralelo


# ============================================================
# ESTRUCTURA ACADÉMICA
# ============================================================

@login_required
@only_director
def estructura_academica(request):
    """
    Muestra la pantalla principal de gestión de la estructura académica.

    Esta vista permite al Director administrar:
    - Gestiones escolares.
    - Niveles académicos.
    - Grados.
    - Paralelos.
    - Requisitos de inscripción.

    También calcula información auxiliar para la interfaz, como:
    - Año actual.
    - Siguiente año sugerido.
    - Si debe mostrarse o no el botón para crear gestión.
    - Grados que ya tienen paralelos activos.

    Template:
    - Structure/structure_academic.html
    """

    # Consulta todas las gestiones, mostrando primero la más reciente.
    gestiones = Gestion.objects.all().order_by("-anio")

    # Consulta niveles activos.
    niveles = Nivel.objects.filter(estado=True)

    # Consulta grados activos junto con su nivel para optimizar consultas.
    grados = Grado.objects.filter(
        estado=True
    ).select_related(
        "nivel"
    )

    # Consulta paralelos activos junto con su grado y nivel.
    paralelos = Paralelo.objects.filter(
        estado=True
    ).select_related(
        "grado__nivel"
    )

    # Consulta los requisitos de inscripción.
    requisitos = Requisito.objects.all().order_by("id")

    # Obtiene los IDs de grados que ya tienen al menos un paralelo activo.
    grados_ocupados = list(
        Paralelo.objects.filter(
            estado=True
        ).values_list(
            "grado_id",
            flat=True
        ).distinct()
    )

    # Año actual del sistema.
    anio_actual = timezone.now().year

    # Por defecto, se permite mostrar el botón para crear gestión.
    mostrar_btn_gestion = True

    # Año sugerido para la siguiente gestión.
    siguiente_anio = anio_actual

    # Si ya existen gestiones, se toma la última para calcular el siguiente año.
    if gestiones.exists():
        ultima_gestion = gestiones.first()
        siguiente_anio = ultima_gestion.anio + 1

        # Si la última gestión es igual o mayor al año actual,
        # no se muestra el botón para crear una nueva gestión.
        if ultima_gestion.anio >= anio_actual:
            mostrar_btn_gestion = False

    context = {
        "gestiones": gestiones,
        "niveles": niveles,
        "grados": grados,
        "paralelos": paralelos,
        "requisitos": requisitos,
        "anio_actual": anio_actual,
        "mostrar_btn_gestion": mostrar_btn_gestion,
        "siguiente_anio": siguiente_anio,
        "form_paralelo": ParaleloForm(),
        "grados_ocupados": grados_ocupados,
    }

    return render(request, "Structure/structure_academic.html", context)


# ============================================================
# GESTIONES ESCOLARES
# ============================================================

@login_required
@only_director
def toggle_gestion(request, pk):
    """
    Activa o desactiva una gestión escolar.

    Reglas:
    - Si la gestión está inactiva, se activa y se desactivan las demás.
    - Si la gestión está activa, se cierra.
    - No se permite reabrir gestiones pasadas.

    Acceso:
    - Solo Director.
    """

    # Busca la gestión seleccionada.
    gestion = get_object_or_404(Gestion, pk=pk)

    # Obtiene el año actual.
    anio_actual = timezone.now().year

    # Evita reabrir una gestión pasada.
    if not gestion.estado and gestion.anio < anio_actual:
        messages.error(
            request,
            f"¡Acción denegada! No puedes reabrir la Gestión {gestion.anio} "
            f"porque ya concluyó."
        )
        return redirect("estructura_academica")

    # Si la gestión está inactiva, se activa.
    if not gestion.estado:
        # Primero se desactivan todas las gestiones.
        Gestion.objects.update(estado=False)

        # Luego se activa solo la gestión seleccionada.
        gestion.estado = True

        messages.success(
            request,
            f"¡La Gestión {gestion.anio} ahora es la gestión activa!"
        )

    # Si la gestión está activa, se cierra.
    else:
        gestion.estado = False

        messages.warning(
            request,
            f"Se ha cerrado la Gestión {gestion.anio}."
        )

    gestion.save()

    return redirect("estructura_academica")


@login_required
@only_director
def crear_gestion(request):
    """
    Crea una nueva gestión escolar y la activa automáticamente.

    Flujo:
    1. Bloquea las gestiones durante la operación para evitar conflictos.
    2. Calcula el nuevo año de gestión.
    3. Cierra las inscripciones activas de la gestión anterior.
    4. Desactiva todas las gestiones.
    5. Crea o recupera la nueva gestión.
    6. Activa la nueva gestión.

    Acceso:
    - Solo Director.

    Nota:
    transaction.atomic() garantiza que la operación sea segura.
    Si algo falla, Django revierte los cambios.
    """

    with transaction.atomic():
        # Bloquea las filas de gestión mientras se crea la nueva.
        gestiones = Gestion.objects.select_for_update().order_by("-anio")

        # Obtiene el año actual.
        anio_actual = timezone.now().year

        # Obtiene la última gestión registrada.
        ultima_gestion = gestiones.first()

        # Calcula el año de la nueva gestión.
        nuevo_anio = ultima_gestion.anio + 1 if ultima_gestion else anio_actual

        # Busca la gestión activa actual para cerrarla.
        gestion_a_cerrar = Gestion.objects.filter(
            estado=True
        ).order_by(
            "-anio"
        ).first()

        # Si no hay gestión activa, se usa la última gestión registrada.
        if not gestion_a_cerrar:
            gestion_a_cerrar = ultima_gestion

        inscripciones_cerradas = 0

        # Si existe una gestión previa, se cierran sus inscripciones activas.
        if gestion_a_cerrar:
            inscripciones_cerradas = Inscripcion.objects.filter(
                gestion=gestion_a_cerrar,
                estado=True
            ).update(
                estado=False
            )

        # Se desactivan todas las gestiones existentes.
        Gestion.objects.all().update(estado=False)

        # Se crea la nueva gestión si no existe.
        nueva_gestion, creada = Gestion.objects.get_or_create(
            anio=nuevo_anio,
            defaults={
                "estado": True
            }
        )

        # Se asegura que la nueva gestión quede activa.
        nueva_gestion.estado = True
        nueva_gestion.save()

    # Mensaje cuando se cerró una gestión anterior.
    if gestion_a_cerrar:
        messages.success(
            request,
            f"¡Gestión {nuevo_anio} creada y activada! "
            f"Se cerraron {inscripciones_cerradas} inscripciones activas "
            f"de la Gestión {gestion_a_cerrar.anio}."
        )

    # Mensaje cuando no había gestión anterior.
    else:
        messages.success(
            request,
            f"¡Gestión {nuevo_anio} creada y activada automáticamente!"
        )

    return redirect("estructura_academica")


# ============================================================
# NIVEL Y GRADO
# ============================================================

@login_required
@only_director
def crear_nivel_grado(request):
    """
    Crea niveles o grados académicos desde un mismo formulario.

    Funcionalidades:
    - Crear un nuevo nivel.
    - Crear un nuevo grado.
    - Restaurar un grado inactivo si se intenta crear nuevamente.
    - Restaurar también sus paralelos asociados si existían.

    Acceso:
    - Solo Director.

    Template:
    - Structure/form_nivel_grade.html
    """

    # Formularios vacíos por defecto.
    form_nivel = NivelForm()
    form_grado = GradoForm()

    # Permite identificar si se está registrando nivel o grado.
    tipo_registro = request.GET.get("tipo")

    if request.method == "POST":

        # ====================================================
        # CREAR NIVEL
        # ====================================================

        if tipo_registro == "nivel" or "btn_guardar_nivel" in request.POST:
            form_nivel = NivelForm(request.POST)

            if form_nivel.is_valid():
                form_nivel.save()

                messages.success(
                    request,
                    "¡Nivel creado exitosamente!"
                )

                return redirect("estructura_academica")

            else:
                # Muestra errores generales del formulario.
                for error in form_nivel.non_field_errors():
                    messages.error(request, error)

        # ====================================================
        # CREAR O RESTAURAR GRADO
        # ====================================================

        elif tipo_registro == "grado" or "btn_guardar_grado" in request.POST:
            nivel_id = request.POST.get("nivel")
            nombre = request.POST.get("nombre")

            # Busca si existe el mismo grado, pero desactivado.
            grado_oculto = Grado.objects.filter(
                nivel_id=nivel_id,
                nombre=nombre,
                estado=False
            ).first()

            # Si el grado existía inactivo, se restaura.
            if grado_oculto:
                grado_oculto.estado = True
                grado_oculto.save()

                # Se restauran también sus paralelos asociados.
                Paralelo.objects.filter(
                    grado=grado_oculto
                ).update(
                    estado=True
                )

                messages.success(
                    request,
                    f"¡El grado '{nombre}' ha sido restaurado exitosamente!"
                )

                return redirect("estructura_academica")

            # Si no existía oculto, se crea normalmente.
            form_grado = GradoForm(request.POST)

            if form_grado.is_valid():
                form_grado.save()

                messages.success(
                    request,
                    "¡Grado creado exitosamente!"
                )

                return redirect("estructura_academica")

            else:
                # Errores generales.
                for error in form_grado.non_field_errors():
                    messages.error(request, error)

                # Errores específicos por campo.
                for field, errors in form_grado.errors.items():
                    if field != "__all__":
                        for error in errors:
                            messages.error(request, f"{error}")

    context = {
        "form_nivel": form_nivel,
        "form_grado": form_grado,
    }

    return render(request, "Structure/form_nivel_grade.html", context)


@login_required
@only_director
def editar_nivel(request, pk):
    """
    Edita un nivel académico existente.

    Acceso:
    - Solo Director.

    Template:
    - Structure/form_nivel_grade.html
    """

    # Busca el nivel por ID.
    nivel = get_object_or_404(Nivel, pk=pk)

    if request.method == "POST":
        form = NivelForm(request.POST, instance=nivel)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"Nivel '{nivel.nombre}' actualizado."
            )

            return redirect("estructura_academica")

    else:
        form = NivelForm(instance=nivel)

    context = {
        "form_nivel": form,
        "form_grado": GradoForm(),
        "editando": True,
    }

    return render(request, "Structure/form_nivel_grade.html", context)


@login_required
@only_director
def eliminar_nivel(request, pk):
    """
    Desactiva un nivel académico.

    Regla:
    - No se puede desactivar un nivel si todavía tiene grados activos.

    Acceso:
    - Solo Director.
    """

    # Busca el nivel.
    nivel = get_object_or_404(Nivel, pk=pk)

    # Verifica si el nivel tiene grados activos.
    if nivel.grados.filter(estado=True).exists():
        messages.error(
            request,
            f"No se puede eliminar '{nivel.nombre}' porque tiene grados registrados. "
            f"Primero debe eliminar los grados asociados."
        )

        return redirect("estructura_academica")

    # Borrado lógico del nivel.
    nivel.estado = False
    nivel.save()

    messages.warning(
        request,
        f"Nivel '{nivel.nombre}' desactivado correctamente."
    )

    return redirect("estructura_academica")


@login_required
@only_director
def editar_grado(request, pk):
    """
    Edita un grado académico existente.

    Regla:
    - No se puede editar un grado si ya tiene paralelos activos.
      Esto protege la integridad de la estructura académica.

    Acceso:
    - Solo Director.

    Template:
    - Structure/form_nivel_grade.html
    """

    # Busca el grado.
    grado = get_object_or_404(Grado, pk=pk)

    # Si el grado ya tiene paralelos activos, no se permite editar.
    if grado.paralelos.filter(estado=True).exists():
        messages.error(
            request,
            f"El grado '{grado.nombre}' ya tiene paralelos configurados. "
            f"No se puede editar para mantener la integridad de los datos."
        )

        return redirect("estructura_academica")

    if request.method == "POST":
        form = GradoForm(request.POST, instance=grado)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"Grado '{grado.nombre}' actualizado correctamente."
            )

            return redirect("estructura_academica")

    else:
        form = GradoForm(instance=grado)

    context = {
        "form_grado": form,
        "form_nivel": NivelForm(),
        "editando_grado": True,
    }

    return render(request, "Structure/form_nivel_grade.html", context)


@login_required
@only_director
def eliminar_grado(request, pk):
    """
    Desactiva un grado académico.

    Reglas:
    - No se puede desactivar si tiene paralelos activos.
    - No se puede desactivar si tiene historial de alumnos inscritos.

    Acceso:
    - Solo Director.
    """

    # Busca el grado.
    grado = get_object_or_404(Grado, pk=pk)

    # No permite desactivar grados con paralelos activos.
    if grado.paralelos.filter(estado=True).exists():
        messages.error(
            request,
            f"No se puede desactivar '{grado.nombre}' porque tiene paralelos activos. "
            f"Elimine primero sus paralelos."
        )

        return redirect("estructura_academica")

    # No permite desactivar grados que tengan historial de inscripciones.
    if Inscripcion.objects.filter(paralelo__grado=grado).exists():
        messages.error(
            request,
            f"El grado '{grado.nombre}' tiene historial de alumnos inscritos. "
            f"No se puede desactivar."
        )

        return redirect("estructura_academica")

    # Borrado lógico del grado.
    grado.estado = False
    grado.save()

    messages.warning(
        request,
        f"Grado '{grado.nombre}' desactivado correctamente."
    )

    return redirect("estructura_academica")


# ============================================================
# PARALELOS
# ============================================================

@login_required
@only_director
def crear_paralelo(request):
    """
    Crea o restaura un paralelo académico.

    Reglas:
    - Los paralelos se crean automáticamente con letras: A, B, C...
    - Cada paralelo tiene cupo máximo inicial de 30.
    - Si existe un paralelo inactivo, se restaura antes de crear uno nuevo.
    - No se puede abrir un grado superior sin tener paralelo activo en el grado anterior.
    - No se puede abrir Primero de Secundaria sin tener Sexto de Primaria activo.

    Acceso:
    - Solo Director.
    """

    if request.method == "POST":
        form = ParaleloForm(request.POST)

        if form.is_valid():
            # Se crea el paralelo en memoria, sin guardar todavía.
            paralelo_temp = form.save(commit=False)

            # Grado seleccionado para el paralelo.
            grado_actual = paralelo_temp.grado

            # Orden jerárquico de grados.
            orden_grados = [
                "Primero",
                "Segundo",
                "Tercero",
                "Cuarto",
                "Quinto",
                "Sexto",
            ]

            # ====================================================
            # VALIDACIÓN DE JERARQUÍA ACADÉMICA
            # ====================================================

            if grado_actual.nombre in orden_grados:
                indice_actual = orden_grados.index(grado_actual.nombre)

                # Para Segundo a Sexto, exige que exista paralelo en el grado anterior.
                if indice_actual > 0:
                    nombre_grado_anterior = orden_grados[indice_actual - 1]

                    grado_anterior = Grado.objects.filter(
                        nivel=grado_actual.nivel,
                        nombre=nombre_grado_anterior,
                        estado=True
                    ).first()

                    if not grado_anterior or not Paralelo.objects.filter(
                        grado=grado_anterior,
                        estado=True
                    ).exists():
                        messages.error(
                            request,
                            f"Jerarquía estricta: Debes tener al menos un paralelo activo "
                            f"en '{nombre_grado_anterior}' de {grado_actual.nivel.nombre} "
                            f"antes de abrir '{grado_actual.nombre}'."
                        )

                        return redirect("estructura_academica")

                # Para Primero de Secundaria, exige Sexto de Primaria activo.
                elif indice_actual == 0 and grado_actual.nivel.nombre == "Secundaria":
                    grado_sexto_primaria = Grado.objects.filter(
                        nivel__nombre="Primaria",
                        nombre="Sexto",
                        estado=True
                    ).first()

                    if not grado_sexto_primaria or not Paralelo.objects.filter(
                        grado=grado_sexto_primaria,
                        estado=True
                    ).exists():
                        messages.error(
                            request,
                            "Jerarquía de Niveles: No puedes abrir "
                            "'Primero de Secundaria' sin tener paralelos activos "
                            "hasta 'Sexto de Primaria'."
                        )

                        return redirect("estructura_academica")

            # ====================================================
            # RESTAURAR PARALELO INACTIVO
            # ====================================================

            # Antes de crear un nuevo paralelo, busca si existe uno inactivo.
            paralelo_oculto = Paralelo.objects.filter(
                grado=grado_actual,
                estado=False
            ).order_by(
                "letra"
            ).first()

            # Si existe paralelo inactivo, se restaura.
            if paralelo_oculto:
                paralelo_oculto.estado = True
                paralelo_oculto.cupo_max = 30
                paralelo_oculto.save()

                messages.success(
                    request,
                    f"Paralelo '{paralelo_oculto.letra}' restaurado automáticamente "
                    f"para {grado_actual.nombre} ({grado_actual.nivel.nombre})."
                )

                return redirect("estructura_academica")

            # ====================================================
            # CREAR NUEVO PARALELO
            # ====================================================

            # Busca el último paralelo histórico del grado.
            ultimo_historico = Paralelo.objects.filter(
                grado=grado_actual
            ).order_by(
                "letra"
            ).last()

            # Si ya existe alguno, genera la siguiente letra.
            if ultimo_historico:
                siguiente_letra = chr(ord(ultimo_historico.letra) + 1)

                # Evita pasar de la letra Z.
                if siguiente_letra > "Z":
                    messages.error(
                        request,
                        f"¡Límite máximo de paralelos alcanzado para {grado_actual.nombre}!"
                    )

                    return redirect("estructura_academica")

                paralelo_temp.letra = siguiente_letra

            # Si no existe ninguno, se crea el paralelo A.
            else:
                paralelo_temp.letra = "A"

            # Configuración inicial del paralelo.
            paralelo_temp.cupo_max = 30
            paralelo_temp.estado = True
            paralelo_temp.save()

            messages.success(
                request,
                f"Paralelo '{paralelo_temp.letra}' generado automáticamente "
                f"para {grado_actual.nombre} ({grado_actual.nivel.nombre})."
            )

        else:
            # Muestra errores del formulario.
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error: {error}")

    return redirect("estructura_academica")


@login_required
@only_director
def eliminar_paralelo(request, pk):
    """
    Desactiva un paralelo académico.

    Reglas:
    - No se puede desactivar si tiene alumnos inscritos.
    - Solo se puede desactivar el último paralelo activo.
    - No se puede vaciar un grado si el siguiente grado depende de él.
    - No se puede vaciar Sexto de Primaria si Primero de Secundaria ya está activo.

    Acceso:
    - Solo Director.
    """

    # Busca el paralelo.
    paralelo = get_object_or_404(Paralelo, pk=pk)

    # Obtiene el grado asociado.
    grado_actual = paralelo.grado

    # No permite desactivar paralelos con historial de inscripción.
    if Inscripcion.objects.filter(paralelo=paralelo).exists():
        messages.error(
            request,
            f"No puedes desactivar el paralelo '{paralelo.letra}' de "
            f"{grado_actual.nombre} porque ya tiene alumnos inscritos."
        )

        return redirect("estructura_academica")

    # Busca el último paralelo activo del mismo grado.
    ultimo_paralelo_activo = Paralelo.objects.filter(
        grado=grado_actual,
        estado=True
    ).order_by(
        "letra"
    ).last()

    # Solo se puede eliminar el último paralelo activo.
    if paralelo.letra != ultimo_paralelo_activo.letra:
        messages.error(
            request,
            f"Secuencia estricta: Para desactivar la letra '{paralelo.letra}', "
            f"primero debes desactivar el paralelo '{ultimo_paralelo_activo.letra}'."
        )

        return redirect("estructura_academica")

    # Cuenta cuántos paralelos activos quedan en ese grado.
    cantidad_paralelos_activos = Paralelo.objects.filter(
        grado=grado_actual,
        estado=True
    ).count()

    # Si es el último paralelo activo del grado, se revisa dependencia jerárquica.
    if cantidad_paralelos_activos == 1:
        orden_grados = [
            "Primero",
            "Segundo",
            "Tercero",
            "Cuarto",
            "Quinto",
            "Sexto",
        ]

        if grado_actual.nombre in orden_grados:
            indice_actual = orden_grados.index(grado_actual.nombre)

            # Si no es Sexto, se verifica si el grado siguiente tiene paralelos activos.
            if indice_actual < len(orden_grados) - 1:
                grado_siguiente_nombre = orden_grados[indice_actual + 1]

                grado_siguiente = Grado.objects.filter(
                    nivel=grado_actual.nivel,
                    nombre=grado_siguiente_nombre,
                    estado=True
                ).first()

                if grado_siguiente and Paralelo.objects.filter(
                    grado=grado_siguiente,
                    estado=True
                ).exists():
                    messages.error(
                        request,
                        f"Jerarquía: No puedes vaciar '{grado_actual.nombre}' "
                        f"porque '{grado_siguiente_nombre}' ya tiene paralelos "
                        f"activos dependientes."
                    )

                    return redirect("estructura_academica")

            # Caso especial:
            # No se permite vaciar Sexto de Primaria si Primero de Secundaria está activo.
            elif indice_actual == 5 and grado_actual.nivel.nombre == "Primaria":
                primero_secundaria = Grado.objects.filter(
                    nivel__nombre="Secundaria",
                    nombre="Primero",
                    estado=True
                ).first()

                if primero_secundaria and Paralelo.objects.filter(
                    grado=primero_secundaria,
                    estado=True
                ).exists():
                    messages.error(
                        request,
                        "Jerarquía de Niveles: No puedes vaciar "
                        "'Sexto de Primaria' porque 'Primero de Secundaria' "
                        "ya tiene paralelos activos."
                    )

                    return redirect("estructura_academica")

    # Nombre descriptivo para el mensaje.
    nombre_completo = (
        f"{grado_actual.nombre} "
        f"'{paralelo.letra}' "
        f"({grado_actual.nivel.nombre})"
    )

    # Borrado lógico del paralelo.
    paralelo.estado = False
    paralelo.save()

    messages.warning(
        request,
        f"Paralelo {nombre_completo} desactivado correctamente."
    )

    return redirect("estructura_academica")
import random
import string
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from students.models import Estudiante, Tutor, Parentesco
from enrollment.models import Inscripcion, EntregaDocumento, Requisito
from academic.models import Gestion, Paralelo
from accounts.models import User


class Command(BaseCommand):
    help = (
        "Carga masiva de estudiantes, tutores, parentescos, "
        "inscripciones 2024 inactivas, inscripciones 2025 activas "
        "y documentos entregados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--por-paralelo",
            type=int,
            default=30,
            help="Cantidad de estudiantes a inscribir por paralelo en 2024"
        )

    def generar_ci(self):
        numero = random.randint(1000000, 9999999)
        expedido = random.choice(["LP", "OR", "CB", "SC", "PT", "CH", "TJ", "BN", "PD"])
        return f"{numero}-{expedido}"

    def generar_rude(self):
        numeros = "".join(random.choices(string.digits, k=10))
        return f"RUDE{numeros}"

    def generar_nombre_por_genero(self):
        nombres_masculinos = [
            "Juan", "Carlos", "Pedro", "Luis", "Miguel",
            "Diego", "Andres", "Mateo", "Samuel", "Daniel",
            "Javier", "Rodrigo", "Gabriel", "Fernando", "Sebastian"
        ]

        nombres_femeninos = [
            "Ana", "Maria", "Carla", "Lucia", "Sofia",
            "Valeria", "Camila", "Fernanda", "Elena", "Paola",
            "Daniela", "Gabriela", "Andrea", "Rosa", "Micaela"
        ]

        genero = random.choice(["M", "F"])

        if genero == "M":
            return random.choice(nombres_masculinos), genero

        return random.choice(nombres_femeninos), genero

    def obtener_edad_minima(self, paralelo):
        grado_nombre = paralelo.grado.nombre.lower()
        nivel_nombre = paralelo.grado.nivel.nombre.lower()

        mapa_primaria = {
            "primero": 6,
            "segundo": 7,
            "tercero": 8,
            "cuarto": 9,
            "quinto": 10,
            "sexto": 11,
        }

        mapa_secundaria = {
            "primero": 12,
            "segundo": 13,
            "tercero": 14,
            "cuarto": 15,
            "quinto": 16,
            "sexto": 17,
        }

        if "primaria" in nivel_nombre:
            for grado, edad in mapa_primaria.items():
                if grado in grado_nombre:
                    return edad

        if "secundaria" in nivel_nombre:
            for grado, edad in mapa_secundaria.items():
                if grado in grado_nombre:
                    return edad

        return 6

    def generar_fecha_nacimiento(self, edad_minima, anio_gestion):
        """
        Genera fecha de nacimiento coherente con la gestión.
        Ejemplo:
        Gestión 2024 + Primero Primaria = 6 o 7 años en 2024.
        """
        edad = random.randint(edad_minima, edad_minima + 1)
        anio_nacimiento = anio_gestion - edad
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)

        return date(anio_nacimiento, mes, dia)

    def obtener_siguiente_paralelo(self, paralelo_actual):
        """
        Determina el paralelo superior:
        Primero Primaria -> Segundo Primaria
        ...
        Sexto Primaria -> Primero Secundaria
        ...
        Quinto Secundaria -> Sexto Secundaria
        Sexto Secundaria -> None
        """
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

        for indice, (nivel, grado) in enumerate(secuencia):
            if nivel in nivel_actual and grado in grado_actual:
                posicion_actual = indice
                break

        if posicion_actual is None:
            return None

        if posicion_actual + 1 >= len(secuencia):
            return None

        siguiente_nivel, siguiente_grado = secuencia[posicion_actual + 1]

        # Primero intenta mantener la misma letra/paralelo.
        siguiente_paralelo = Paralelo.objects.filter(
            estado=True,
            letra=letra_actual,
            grado__nombre__icontains=siguiente_grado,
            grado__nivel__nombre__icontains=siguiente_nivel,
        ).first()

        if siguiente_paralelo:
            return siguiente_paralelo

        # Si no existe la misma letra, usa cualquier paralelo del curso superior.
        return Paralelo.objects.filter(
            estado=True,
            grado__nombre__icontains=siguiente_grado,
            grado__nivel__nombre__icontains=siguiente_nivel,
        ).first()

    def crear_entregas_documento(self, inscripcion, requisitos):
        total = 0

        for requisito in requisitos:
            EntregaDocumento.objects.create(
                inscripcion=inscripcion,
                requisito=requisito,
                estado=True,
            )
            total += 1

        return total

    def crear_inscripcion(self, estudiante, gestion, paralelo, usuario, estado, observacion):
        rude = self.generar_rude()

        while Inscripcion.objects.filter(rude=rude).exists():
            rude = self.generar_rude()

        return Inscripcion.objects.create(
            estudiante=estudiante,
            gestion=gestion,
            paralelo=paralelo,
            usuario=usuario,
            estado=estado,
            observacion=observacion,
            rude=rude,
        )

    def handle(self, *args, **options):
        por_paralelo = options["por_paralelo"]

        nombres_masculinos_tutor = [
            "Juan", "Carlos", "Pedro", "Luis", "Miguel",
            "Diego", "Andres", "Mateo", "Samuel", "Daniel",
            "Javier", "Rodrigo", "Gabriel", "Fernando", "Sebastian"
        ]

        nombres_femeninos_tutor = [
            "Ana", "Maria", "Carla", "Lucia", "Sofia",
            "Valeria", "Camila", "Fernanda", "Elena", "Paola",
            "Daniela", "Gabriela", "Andrea", "Rosa", "Micaela"
        ]

        apellidos = [
            "Mamani", "Quispe", "Choque", "Condori", "Flores",
            "Vargas", "Rojas", "Gutierrez", "Fernandez", "Lopez",
            "Teran", "Limari", "Sanchez", "Ramirez", "Morales",
            "Calle", "Arce", "Paredes", "Aguilar", "Mendoza"
        ]

        relaciones = ["Padre", "Madre", "Tutor legal", "Apoderado"]

        ocupaciones = [
            "Comerciante", "Profesor", "Chofer", "Ama de casa",
            "Ingeniero", "Enfermera", "Albañil", "Abogado",
            "Contador", "Agricultor", "Mecánico", "Secretaria"
        ]

        # Gestión 2024: histórica/inactiva.
        gestion_2024, creada_2024 = Gestion.objects.get_or_create(
            anio=2024,
            defaults={"estado": False}
        )

        if gestion_2024.estado is not False:
            gestion_2024.estado = False
            gestion_2024.save()

        # Gestión 2025: historica/inactiva.
        gestion_2025, creada_2025 = Gestion.objects.get_or_create(
            anio=2025,
            defaults={"estado": False}
        )

        if gestion_2025.estado is not False:
            gestion_2025.estado = False
            gestion_2025.save()

        if creada_2024:
            self.stdout.write(self.style.WARNING("Se creó la gestión 2024 inactiva."))
        else:
            self.stdout.write(self.style.SUCCESS("Se usará la gestión 2024 inactiva."))

        if creada_2025:
            self.stdout.write(self.style.WARNING("Se creó la gestión 2025 inactiva."))
        else:
            self.stdout.write(self.style.SUCCESS("Se usará la gestión 2025 inactiva."))

        usuario = User.objects.filter(is_active=True).first()

        if not usuario:
            self.stdout.write(
                self.style.ERROR("No existe un usuario activo para registrar inscripciones.")
            )
            return

        paralelos = Paralelo.objects.filter(estado=True).select_related(
            "grado",
            "grado__nivel"
        ).order_by(
            "grado__nivel__nombre",
            "grado__nombre",
            "letra"
        )

        if not paralelos.exists():
            self.stdout.write(
                self.style.ERROR("No existen paralelos activos.")
            )
            return

        requisitos = Requisito.objects.filter(estado=True)

        if not requisitos.exists():
            self.stdout.write(
                self.style.ERROR("No existen requisitos activos para entregar documentos.")
            )
            return

        total_estudiantes = 0
        total_tutores = 0
        total_parentescos = 0
        total_inscripciones_2024 = 0
        total_inscripciones_2025 = 0
        total_documentos = 0
        total_sin_promocion = 0

        with transaction.atomic():
            for paralelo in paralelos:
                edad_minima = self.obtener_edad_minima(paralelo)
                siguiente_paralelo = self.obtener_siguiente_paralelo(paralelo)

                self.stdout.write(
                    f"Generando {por_paralelo} estudiantes en "
                    f"{paralelo.grado.nombre} de {paralelo.grado.nivel.nombre} {paralelo.letra} para 2024..."
                )

                if siguiente_paralelo:
                    self.stdout.write(
                        f"Promoción 2025: "
                        f"{paralelo.grado.nombre} de {paralelo.grado.nivel.nombre} {paralelo.letra} "
                        f"-> "
                        f"{siguiente_paralelo.grado.nombre} de {siguiente_paralelo.grado.nivel.nombre} {siguiente_paralelo.letra}"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No se encontró curso superior para "
                            f"{paralelo.grado.nombre} de {paralelo.grado.nivel.nombre} {paralelo.letra}. "
                            f"Solo se creará inscripción 2024."
                        )
                    )

                for _ in range(por_paralelo):
                    ci_estudiante = self.generar_ci()

                    while Estudiante.objects.filter(cedula_identidad=ci_estudiante).exists():
                        ci_estudiante = self.generar_ci()

                    nombre_estudiante, genero_estudiante = self.generar_nombre_por_genero()

                    apellido_paterno_estudiante = random.choice(apellidos)
                    apellido_materno_estudiante = random.choice(apellidos)

                    estudiante = Estudiante.objects.create(
                        cedula_identidad=ci_estudiante,
                        nombres=nombre_estudiante,
                        apellido_paterno=apellido_paterno_estudiante,
                        apellido_materno=apellido_materno_estudiante,
                        correo_electronico=f"estudiante{random.randint(10000, 99999)}@correo.com",
                        direccion=f"Zona Central #{random.randint(1, 500)}",
                        estado=True,
                        fecha_nacimiento=self.generar_fecha_nacimiento(
                            edad_minima=edad_minima,
                            anio_gestion=gestion_2024.anio
                        ),
                        genero=genero_estudiante,
                    )

                    total_estudiantes += 1

                    ci_tutor = self.generar_ci()

                    while Tutor.objects.filter(cedula_identidad=ci_tutor).exists():
                        ci_tutor = self.generar_ci()

                    relacion = random.choice(relaciones)

                    if relacion == "Padre":
                        nombre_tutor = random.choice(nombres_masculinos_tutor)
                        apellidos_tutor = f"{apellido_paterno_estudiante} {random.choice(apellidos)}"

                    elif relacion == "Madre":
                        nombre_tutor = random.choice(nombres_femeninos_tutor)
                        apellidos_tutor = f"{apellido_materno_estudiante} {random.choice(apellidos)}"

                    else:
                        nombre_tutor = random.choice(
                            nombres_masculinos_tutor + nombres_femeninos_tutor
                        )
                        apellido_relacionado = random.choice([
                            apellido_paterno_estudiante,
                            apellido_materno_estudiante
                        ])
                        apellidos_tutor = f"{apellido_relacionado} {random.choice(apellidos)}"

                    tutor = Tutor.objects.create(
                        cedula_identidad=ci_tutor,
                        nombres=nombre_tutor,
                        apellidos=apellidos_tutor,
                        celular=f"7{random.randint(1000000, 9999999)}",
                        estado=True,
                        fecha_baja=None,
                        ocupacion=random.choice(ocupaciones),
                    )

                    total_tutores += 1

                    Parentesco.objects.create(
                        estudiante=estudiante,
                        tutor=tutor,
                        relacion=relacion,
                    )

                    total_parentescos += 1

                    # Inscripción 2024 inactiva.
                    inscripcion_2024 = self.crear_inscripcion(
                        estudiante=estudiante,
                        gestion=gestion_2024,
                        paralelo=paralelo,
                        usuario=usuario,
                        estado=False,
                        observacion="Inscripción 2024 generada automáticamente para pruebas. Estado inactivo.",
                    )

                    total_inscripciones_2024 += 1
                    total_documentos += self.crear_entregas_documento(
                        inscripcion=inscripcion_2024,
                        requisitos=requisitos
                    )

                    # Inscripción 2025 activa en curso superior.
                    if siguiente_paralelo:
                        inscripcion_2025 = self.crear_inscripcion(
                            estudiante=estudiante,
                            gestion=gestion_2025,
                            paralelo=siguiente_paralelo,
                            usuario=usuario,
                            estado=False,
                            observacion="Inscripción 2025 generada automáticamente por promoción de curso. Estado inactivo.",
                        )

                        total_inscripciones_2025 += 1
                        total_documentos += self.crear_entregas_documento(
                            inscripcion=inscripcion_2025,
                            requisitos=requisitos
                        )
                    else:
                        total_sin_promocion += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Proceso completado:\n"
                f"- Estudiantes creados: {total_estudiantes}\n"
                f"- Tutores creados: {total_tutores}\n"
                f"- Parentescos creados: {total_parentescos}\n"
                f"- Inscripciones 2024 inactivas: {total_inscripciones_2024}\n"
                f"- Inscripciones 2025 inactivas: {total_inscripciones_2025}\n"
                f"- Entregas de documentos creadas: {total_documentos}\n"
                f"- Estudiantes sin promoción 2025: {total_sin_promocion}"
            )
        )
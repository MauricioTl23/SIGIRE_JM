from django.core.management.base import BaseCommand
from django.db import transaction

from students.models import Estudiante, Tutor, Parentesco
from enrollment.models import Inscripcion, EntregaDocumento
from academic.models import Gestion


class Command(BaseCommand):
    help = "Limpia estudiantes, tutores, parentescos, inscripciones y documentos de las gestiones 2024 y 2025"

    def handle(self, *args, **options):
        gestiones = Gestion.objects.filter(anio__in=[2024, 2025])

        if not gestiones.exists():
            self.stdout.write(
                self.style.ERROR("No existen gestiones 2024 ni 2025.")
            )
            return

        inscripciones = Inscripcion.objects.filter(gestion__in=gestiones)

        estudiantes_pks = list(
            inscripciones.values_list("estudiante_id", flat=True)
        )

        parentescos = Parentesco.objects.filter(
            estudiante_id__in=estudiantes_pks
        )

        tutores_pks = list(
            parentescos.values_list("tutor_id", flat=True)
        )

        with transaction.atomic():
            entregas_eliminadas, _ = EntregaDocumento.objects.filter(
                inscripcion__in=inscripciones
            ).delete()

            inscripciones_eliminadas, _ = inscripciones.delete()

            parentescos_eliminados, _ = parentescos.delete()

            tutores_eliminados, _ = Tutor.objects.filter(
                pk__in=tutores_pks
            ).delete()

            estudiantes_eliminados, _ = Estudiante.objects.filter(
                pk__in=estudiantes_pks
            ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Limpieza completada:\n"
                f"- Entregas de documentos eliminadas: {entregas_eliminadas}\n"
                f"- Inscripciones eliminadas: {inscripciones_eliminadas}\n"
                f"- Parentescos eliminados: {parentescos_eliminados}\n"
                f"- Tutores eliminados: {tutores_eliminados}\n"
                f"- Estudiantes eliminados: {estudiantes_eliminados}"
            )
        )
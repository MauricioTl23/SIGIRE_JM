document.addEventListener("DOMContentLoaded", function() {

    if (typeof configEstudiante !== 'undefined' && configEstudiante.mostrarPregunta) {
        
        Swal.fire({
            title: '¿Ya registró al tutor?',
            text: "Para registrar un estudiante, primero debe existir un tutor en el sistema.",
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#3b82f6', 
            cancelButtonColor: '#64748b',  
            confirmButtonText: 'Sí, ya está registrado',
            cancelButtonText: 'No, registrar tutor ahora',
            allowOutsideClick: false,
            allowEscapeKey: false
        }).then((result) => {
            if (result.isConfirmed) {
                window.location.href = configEstudiante.urlListaTutores;
            } else {
                Swal.fire({
                    title: 'Paso 1: Registrar Tutor',
                    text: 'A continuación, por favor llene los datos del tutor. Cuando termine, el sistema lo traerá de vuelta aquí para registrar al estudiante.',
                    icon: 'info',
                    confirmButtonColor: '#3b82f6',
                    confirmButtonText: 'Entendido, continuar',
                    allowOutsideClick: false
                }).then(() => {
                    window.location.href = configEstudiante.urlRegistrarTutor;
                });
            }
        });
        
    }
});
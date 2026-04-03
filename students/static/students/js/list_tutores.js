document.addEventListener("DOMContentLoaded", function() {

    const urlParams = new URLSearchParams(window.location.search);
    const nuevoTutorId = urlParams.get('nuevo_tutor_id');


    if (nuevoTutorId) {
        Swal.fire({
            title: '¡Tutor guardado!',
            text: "¿Desea registrar ahora al estudiante asociado a este tutor?",
            icon: 'success',
            showCancelButton: true,
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            confirmButtonText: '<i class="fa-solid fa-user-plus"></i> Sí, registrar estudiante',
            cancelButtonText: 'No, después',
            allowOutsideClick: false
        }).then((result) => {
            if (result.isConfirmed) {
                
                window.location.href = "/crear-estudiante/?tutor_id=" + nuevoTutorId;
            } else {
                
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        });
    }
});
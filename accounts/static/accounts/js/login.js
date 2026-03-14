document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. FUNCIÓN PARA MOSTRAR/OCULTAR CONTRASEÑA ---
    const togglePassword = document.getElementById('togglePassword');
    // Django asigna automáticamente el id 'id_password' al campo de contraseña
    const passwordField = document.getElementById('id_password'); 

    if (togglePassword && passwordField) {
        togglePassword.addEventListener('click', function () {
            // Alternar el tipo de input entre 'password' y 'text'
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            // Alternar el icono del ojo (tachado vs normal)
            this.classList.toggle('bi-eye');
            this.classList.toggle('bi-eye-slash');
        });
    }

    // --- 2. EFECTO DE CARGA EN EL BOTÓN AL ENVIAR ---
    const loginForm = document.querySelector('form');
    const submitBtn = document.querySelector('.btn-login');

    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', function() {
            // Deshabilitamos el botón para evitar múltiples clics
            submitBtn.disabled = true;
            
            // Cambiamos el texto e insertamos un spinner de Bootstrap
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Iniciando...';
            
            // Le bajamos un poco la opacidad para que se vea que está procesando
            submitBtn.style.opacity = '0.8';
        });
    }
});
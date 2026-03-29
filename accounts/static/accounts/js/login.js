document.addEventListener('DOMContentLoaded', function() {

    const togglePassword = document.getElementById('togglePassword');
    const passwordField = document.getElementById('id_password'); 

    if (togglePassword && passwordField) {
        togglePassword.addEventListener('click', function () {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
          
            this.classList.toggle('bi-eye');
            this.classList.toggle('bi-eye-slash');
        });
    }

    
    const loginForm = document.querySelector('form');
    const submitBtn = document.querySelector('.btn-login');

    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', function() {
            
            submitBtn.disabled = true;
            
            
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Iniciando...';
            
            
            submitBtn.style.opacity = '0.8';
        });
    }
});
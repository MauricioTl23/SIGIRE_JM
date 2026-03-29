document.addEventListener('DOMContentLoaded', function() {
    
    // --- Función para Capitalizar Nombres (Ejem: mauricio dimas -> Mauricio Dimas) ---
    const capitalizarTexto = function() {
        let valor = this.value;
        // Solo permitimos letras y espacios
        valor = valor.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
        
        // Convertimos a "Title Case"
        this.value = valor.split(' ').map(palabra => {
            if (palabra.length > 0) {
                return palabra.charAt(0).toUpperCase() + palabra.slice(1).toLowerCase();
            }
            return palabra;
        }).join(' ');
    };

    const inputsNombre = document.querySelector('input[name="first_name"]');
    const inputsApellido = document.querySelector('input[name="last_name"]');

    if (inputsNombre) inputsNombre.addEventListener('input', capitalizarTexto);
    if (inputsApellido) inputsApellido.addEventListener('input', capitalizarTexto);

    // --- Validación de Celular (8 dígitos numéricos) ---
    const celularInput = document.querySelector('input[name="celular"]');
    if (celularInput) {
        celularInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8);
        });
    }

    // --- Validación de C.I. (Números, máx 10) ---
    const ciInput = document.querySelector('input[name="cedula_identidad"]');
    if (ciInput) {
        ciInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    }

    // --- Validación de Complemento (2 alfanuméricos en Mayúsculas) ---
    const complementoInput = document.querySelector('input[name="complemento"]');
    if (complementoInput) {
        complementoInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 2);
        });
    }
});
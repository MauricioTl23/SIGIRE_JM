document.addEventListener('DOMContentLoaded', function() {
    
    const capitalizarTexto = function() {
        let valor = this.value;
        
        valor = valor.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
        
        
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

  
    const celularInput = document.querySelector('input[name="celular"]');
    if (celularInput) {
        celularInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8);
        });
    }

    
    const ciInput = document.querySelector('input[name="cedula_identidad"]');
    if (ciInput) {
        ciInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    }

    
    const complementoInput = document.querySelector('input[name="complemento"]');
    if (complementoInput) {
        complementoInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 2);
        });
    }
});
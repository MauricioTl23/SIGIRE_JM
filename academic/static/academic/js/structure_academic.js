// Funciones del Modal
function abrirModal() {
  document.getElementById('modalParalelo').style.display = 'flex';
  document.getElementById('filtro_nivel').selectedIndex = 0;
  filtrarGrados();
}

function cerrarModal() {
  document.getElementById('modalParalelo').style.display = 'none';
}

window.onclick = function (event) {
  var modal = document.getElementById('modalParalelo');
  if (event.target == modal) {
    cerrarModal();
  }
}

function filtrarGrados() {
  let nivelSelect = document.getElementById('filtro_nivel');
  let gradoSelect = document.getElementById('select_grado');
  if(!nivelSelect || !gradoSelect) return; // Protección extra

  let nivelNombre = nivelSelect.options[nivelSelect.selectedIndex].text;

  for (let i = 0; i < gradoSelect.options.length; i++) {
    let option = gradoSelect.options[i];
    if (!option.hasAttribute('data-original-text')) {
      option.setAttribute('data-original-text', option.text);
    }
    let textoOriginal = option.getAttribute('data-original-text');

    if (option.value === '') {
      option.style.display = 'block';
      continue;
    }

    if (nivelNombre === '-- Elige Nivel --') {
      option.style.display = 'none';
    } else if (textoOriginal.includes(nivelNombre)) {
      option.style.display = 'block';
      option.text = textoOriginal.split('-')[0].trim();
    } else {
      option.style.display = 'none';
    }
  }
  gradoSelect.value = '';
}

// Inicialización cuando carga la página
document.addEventListener('DOMContentLoaded', function () {
  console.log("El archivo JS se cargó correctamente.");
  filtrarGrados();

  // Interceptor de clics
  document.body.addEventListener('click', function (event) {
    let botonEliminar = event.target.closest('.alerta-eliminar');

    if (botonEliminar) {
      console.log("¡Clic detectado en un botón de eliminar!");
      event.preventDefault();

      let urlEliminar = botonEliminar.getAttribute('href');
      let nombreItem = botonEliminar.getAttribute('data-nombre') || "este elemento";
      let textoExtra = botonEliminar.getAttribute('data-extra') || "";

      console.log("🔗 URL destino:", urlEliminar);

      // Verificamos si la librería SweetAlert existe en esta página
      if (typeof Swal === 'undefined') {
          console.error("ERROR: SweetAlert2 no está cargado. Usando alerta de respaldo.");
          if(confirm(`¿Estás seguro de eliminar ${nombreItem}?`)) {
              window.location.href = urlEliminar;
          }
          return;
      }

      console.log("Lanzando SweetAlert...");
      Swal.fire({
        title: '¿Estás seguro?',
        text: textoExtra ? textoExtra : `Estás a punto de eliminar ${nombreItem}. Esta acción no se puede deshacer.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#64748b',
        confirmButtonText: '<i class="fa-solid fa-trash-can"></i> Sí, eliminar',
        cancelButtonText: 'Cancelar',
        reverseButtons: true
      }).then((result) => {
        if (result.isConfirmed) {
          console.log("Confirmado. Redirigiendo...");
          window.location.href = urlEliminar;
        } else {
          console.log("Cancelado por el usuario.");
        }
      });
    }
  });
});
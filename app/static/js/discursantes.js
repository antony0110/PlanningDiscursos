// Lógica para cargar, buscar y mostrar discursantes
let modalWAInstance = null;
let modalPDFInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar modales de Bootstrap
    const elemWA = document.getElementById('modalWhatsapp');
    const elemPDF = document.getElementById('modalPDF');
    if (elemWA) modalWAInstance = new bootstrap.Modal(elemWA);
    if (elemPDF) modalPDFInstance = new bootstrap.Modal(elemPDF);
    
    // Asignar el próximo domingo por defecto
    const hoy = new Date();
    const proximoDomingo = new Date(hoy.setDate(hoy.getDate() + ((7 - hoy.getDay()) % 7)));
    const fechaDefault = proximoDomingo.toISOString().split('T')[0];
    
    const inputFechaInv = document.getElementById('fechaInvitacion');
    const inputPdfFecha = document.getElementById('pdfFecha');
    
    if (inputFechaInv) inputFechaInv.value = fechaDefault;
    if (inputPdfFecha) inputPdfFecha.value = fechaDefault;

    cargarCongregaciones();
    filtrarPorCongregacion();

    // 👉 MÉTELO AQUÍ DENTRO:
    if (typeof cargarCongregacionesEnSelects === 'function') {
        cargarCongregacionesEnSelects();
    }

    const selectNuevo = document.getElementById('nuevo-orador-congre');
    if (selectNuevo) {
        selectNuevo.onchange = function() { verificarNuevaCongregacion(this); };
    }

    const selectEditar = document.getElementById('editar-orador-congre');
    if (selectEditar) {
        selectEditar.onchange = function() { verificarNuevaCongregacion(this); };
    }
});
async function cargarCongregacionesEnSelects() {
    try {
        const response = await fetch('/api/congregaciones');
        const congregaciones = await response.json();
        
        let opcionesHTML = '<option value="">Selecciona congregación...</option>';
        congregaciones.forEach(c => {
            opcionesHTML += `<option value="${c.id}">${c.nombre}</option>`;
        });
        
        // Añadir la opción especial al final
        opcionesHTML += '<option value="NUEVA_CONGREGACION">➕ Añadir nueva congregación...</option>';
        
        // Asignar a ambos selects (Crear y Editar)
        const selectNuevo = document.getElementById('nuevo-orador-congre');
        const selectEditar = document.getElementById('editar-orador-congre');
        
        if (selectNuevo) selectNuevo.innerHTML = opcionesHTML;
        if (selectEditar) selectEditar.innerHTML = opcionesHTML;
        
    } catch (error) {
        console.error("Error al cargar las congregaciones:", error);
    }
}

// Renderizar la tabla de oradores actualizada para incluir congregación y botones de acción
function renderTabla(oradores) {
    listaOradoresGlobal = oradores;

    if (typeof cargarOradoresEnDesplegable === 'function') {
        cargarOradoresEnDesplegable(oradores);
    }

    const tbody = document.getElementById('tablaOradores');
    if (!tbody) return;

    if (oradores.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No se encontraron oradores.</td></tr>';
        return;
    }
    
    const selectCongregacion = document.getElementById('selectCongregacion');

    tbody.innerHTML = oradores.map((o) => {
        let nombreCongre = '-';

        if (o.congregacion) {
            if (typeof o.congregacion === 'object') {
                nombreCongre = o.congregacion.nombre || o.congregacion.nombre_congregacion || '-';
            } else if (typeof o.congregacion === 'string') {
                nombreCongre = o.congregacion;
            }
        } 
        
        if (nombreCongre === '-' && o.congregacion_id && selectCongregacion) {
            const option = selectCongregacion.querySelector(`option[value="${o.congregacion_id}"]`);
            if (option) nombreCongre = option.textContent;
        }
        
        return `
        <tr>
            <td>
                <strong>${o.nombre}</strong>
                ${o.es_coordinador ? '<span class="badge bg-warning text-dark ms-1">Coord</span>' : ''}
            </td>
            <td>${o.cargo || '-'}</td>
            <td>${o.telefono || '-'}</td>
            <td>
                ${(o.discursos || []).map(d => `<span class="badge badge-discurso ms-1">${d.numero_discurso || d.numero || d}</span>`).join('')}
            </td>
            <td>${nombreCongre}</td>
            <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-primary" onclick="abrirModalEditarOrador(${o.id})" title="Editar Orador">
                    <i class="bi bi-pencil-fill"></i>
                </button>
                <button onclick="eliminarOrador(${o.id})" class="btn btn-sm btn-outline-danger" title="Eliminar orador">
                    <i class="bi bi-trash-fill"></i>
                </button>
            </td>
        </tr>`;
    }).join('');
}

// Filtros y Búsquedas
async function buscarPorDiscurso() {
    const num = document.getElementById('numDiscurso').value;
    if (!num) return;
    const res = await fetch(`/api/oradores/buscar-por-discurso?numero=${num}`);
    const data = await res.json();
    renderTabla(data);
}

async function filtrarPorCongregacion() {
    const select = document.getElementById('selectCongregacion');
    const id = select ? select.value : '';
    const url = id ? `/api/oradores?congregacion_id=${id}` : '/api/oradores';
    const res = await fetch(url);
    const data = await res.json();
    renderTabla(data);
}

// Formato de Fecha
function formatearFechaEspanol(fechaStr) {
    if (!fechaStr) return "____";
    const partes = fechaStr.split('-');
    const fecha = new Date(partes[0], partes[1] - 1, partes[2]);
    return fecha.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
}

// Lógica de Mensajes WhatsApp
function generarMensaje(index) {
    const orador = listaOradoresGlobal[index];
    const fechaRaw = document.getElementById('fechaInvitacion').value;
    const fechaFormateada = formatearFechaEspanol(fechaRaw);
    const primerNombre = orador.nombre.split(' ')[0];

    let mensaje = `Hola buenos días ${primerNombre} :\n\n`;
    mensaje += `Soy Antony, de la congregación de Algemesí. Te escribo porque me gustaría invitarte a dar un discurso en nuestra congregación el día *${fechaFormateada}*\n\n`;
    mensaje += `Te adjunto la invitación con toda la información. ¿Podrías confirmarme cuanto antes si vas a poder venir?\n\n`;
    mensaje += `Muchas gracias.\n¡Un abrazo!`;

    document.getElementById('textoWhatsapp').innerText = mensaje;
    
    let telefonoLimpio = (orador.telefono || '').replace(/\D/g, '');
    if (telefonoLimpio.length === 9) telefonoLimpio = '34' + telefonoLimpio;

    const btnWA = document.getElementById('btnAbrirWA');
    if (telefonoLimpio) {
        btnWA.href = `https://wa.me/${telefonoLimpio}?text=${encodeURIComponent(mensaje)}`;
        btnWA.classList.remove('disabled');
    } else {
        btnWA.href = "#";
        btnWA.classList.add('disabled');
    }

    if (modalWAInstance) modalWAInstance.show();
}

function copiarMensaje() {
    const texto = document.getElementById('textoWhatsapp').innerText;
    navigator.clipboard.writeText(texto).then(() => alert('¡Mensaje copiado!'));
}

// Cargar congregaciones en el select del modal al abrirlo
document.getElementById('modalNuevoOrador')?.addEventListener('show.bs.modal', async () => {
    try {
        const res = await fetch('/api/congregaciones');
        const congregaciones = await res.json();
        
        const select = document.getElementById('nuevo-orador-congre');
        select.innerHTML = '<option value="">Selecciona congregación...</option>' +
            congregaciones.map(c => `<option value="${c.id}">${c.nombre}</option>`).join('');
    } catch (err) {
        console.error("Error al cargar congregaciones:", err);
    }
});

// Cargar congregaciones en el select del modal al abrirlo (con opción de añadir nueva)
document.getElementById('modalNuevoOrador')?.addEventListener('show.bs.modal', async () => {
    try {
        const res = await fetch('/api/congregaciones');
        const congregaciones = await res.json();
        
        const select = document.getElementById('nuevo-orador-congre');
        if (select) {
            let opcionesHTML = '<option value="">Selecciona congregación...</option>';
            congregaciones.forEach(c => {
                opcionesHTML += `<option value="${c.id}">${c.nombre}</option>`;
            });
            opcionesHTML += '<option value="NUEVA_CONGREGACION">➕ Añadir nueva congregación...</option>';
            
            select.innerHTML = opcionesHTML;
            select.onchange = function() { verificarNuevaCongregacion(this); };
        }
    } catch (err) {
        console.error("Error al cargar congregaciones:", err);
    }
});
async function guardarNuevoOrador() {
    const nombre = document.getElementById('nuevo-orador-nombre').value;
    const telefono = document.getElementById('nuevo-orador-telefono').value;
    const congregacion_id = document.getElementById('nuevo-orador-congre').value;
    const discursosStr = document.getElementById('nuevo-orador-discursos').value;

    const discursos = discursosStr.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d));

    const datosAEnviar = {
        nombre: nombre,
        telefono: telefono,
        congregacion_id: congregacion_id && congregacion_id !== 'NUEVA_CONGREGACION' ? parseInt(congregacion_id) : null,
        discursos: discursos
    };

    try {
        // Importante: incluir /api al principio de la ruta
        const response = await fetch('/api/oradores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datosAEnviar)
        });

        if (response.ok) {
            const modalEl = document.getElementById('modalNuevoOrador'); // Ajusta el ID de tu modal si es distinto
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            if (typeof cargarOradores === 'function') {
                cargarOradores();
            } else {
                location.reload();
            }
        } else {
            const errorData = await response.json();
            alert(`Error: ${errorData.detail || 'No se pudo crear el orador'}`);
        }
    } catch (error) {
        console.error('Error de red:', error);
        alert('Error de conexión al crear el orador.');
    }
}

async function eliminarOrador(oradorId) {
    // 1. Primera pregunta: ¿Estás seguro de que quieres eliminar?
    const confirmar = window.confirm("¿Estás seguro de que quieres eliminar este orador?");
    if (!confirmar) return; // Si le da a cancelar, no hace nada

    try {
        const response = await fetch(`/api/${oradorId}`, {
            method: 'DELETE'
        });

        // 2. Si el servidor responde con 409 (significa que está puesto en la planificación)
        if (response.status === 409) {
            const data = await response.json();
            
            // Muestra el mensaje del backend advirtiendo que tiene fechas en la planificación
            const confirmarForzar = window.confirm(data.detail + "\n\n¿Deseas continuar y borrarlo de todos modos?");
            
            if (confirmarForzar) {
                await forzarEliminacionOrador(oradorId);
            }
            return;
        }

        if (!response.ok) {
            throw new Error("No se pudo eliminar el discursante.");
        }

        const resultado = await response.json();
        alert(resultado.mensaje);
        location.reload(); 

    } catch (error) {
        console.error("Error al eliminar:", error);
        alert("Ocurrió un error inesperado al intentar borrar el orador.");
    }
}

// Función auxiliar para forzar el borrado cuando el usuario acepta la advertencia
async function forzarEliminacionOrador(oradorId) {
    try {
        // CORREGIDO: Ajustado a la ruta real de tu backend (/api/{id}?forzar=true)
        const response = await fetch(`/api/${oradorId}?forzar=true`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error("Error al forzar la eliminación.");
        }

        const resultado = await response.json();
        alert(resultado.mensaje);
        location.reload();

    } catch (error) {
        console.error("Error al forzar borrado:", error);
        alert("No se pudo completar el borrado forzoso.");
    }
}

// 1. Abrir el modal y cargar los datos correctamente sin disparar eventos fantasma
function abrirModalEditarOrador(id) {
    const orador = listaOradoresGlobal.find(o => o.id === id);
    if (!orador) return;

    window.oradorEditandoId = id;

    document.getElementById('editar-orador-nombre').value = orador.nombre || '';
    document.getElementById('editar-orador-telefono').value = orador.telefono || '';
    
    // Obtener el ID de la congregación de forma segura (sea número, texto u objeto)
    const congreId = orador.congregacion_id || (orador.congregacion && orador.congregacion.id) || orador.congregacion || '';
    
    // Cargar congregaciones y asignar el valor actual sin activar el prompt
    cargarCongregacionesEnModal('editar-orador-congre', congreId);

    const discursosArray = (orador.discursos || []).map(d => d.numero_discurso || d.numero || d);
    document.getElementById('editar-orador-discursos').value = discursosArray.join(', ');

    const modalElement = document.getElementById('modalEditarOrador');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

// 2. Rellenar el selector y controlar el evento change de forma segura
function cargarCongregacionesEnModal(selectId, congregacionIdActual) {
    const select = document.getElementById(selectId);
    if (!select) return;

    select.innerHTML = '';
    const selectPrincipal = document.getElementById('selectCongregacion');
    
    if (selectPrincipal) {
        Array.from(selectPrincipal.options).forEach(opt => {
            if (opt.value !== "") { // Ignorar la opción vacía de "Todas"
                select.add(opt.cloneNode(true));
            }
        });
    }

    const optionNueva = document.createElement('option');
    optionNueva.value = 'NUEVA_CONGREGACION';
    optionNueva.textContent = '➕ Añadir nueva congregación...';
    select.appendChild(optionNueva);

    // Asignar el valor actual si lo tiene
    if (congregacionIdActual) {
        select.value = congregacionIdActual;
    }

    // Vincular el evento change por código para que solo salte cuando el usuario haga clic a propósito
    select.onchange = function() {
        verificarNuevaCongregacion(this);
    };
}

async function verificarNuevaCongregacion(selectElement) {
    if (selectElement.value === 'NUEVA_CONGREGACION') {
        const nuevaCongre = prompt('Introduce el nombre de la nueva congregación:');
        if (nuevaCongre && nuevaCongre.trim() !== '') {
            try {
                // Importante: añadir /api aquí también
                const response = await fetch('/api/congregaciones', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: nuevaCongre.trim() })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const nuevaId = data.id || data.nombre;

                    // Actualizar todos los desplegables de la página añadiendo la nueva opción antes de "NUEVA_CONGREGACION"
                    const selects = document.querySelectorAll('#nuevo-orador-congre, #editar-orador-congre, #selectCongregacion');
                    selects.forEach(s => {
                        const opt = document.createElement('option');
                        opt.value = nuevaId;
                        opt.textContent = nuevaCongre.trim();
                        
                        // Insertarla antes de la última opción (que es la de crear nueva)
                        s.insertBefore(opt, s.lastElementChild);
                    });

                    selectElement.value = nuevaId;
                } else {
                    alert('Error al guardar la congregación en el servidor.');
                    selectElement.value = '';
                }
            } catch (error) {
                console.error('Error:', error);
                alert('No se pudo conectar con el servidor.');
                selectElement.value = '';
            }
        } else {
            selectElement.value = '';
        }
    }
}

async function guardarEdicionOrador() {
    const id = window.oradorEditandoId;
    const nombre = document.getElementById('editar-orador-nombre').value;
    const telefono = document.getElementById('editar-orador-telefono').value;
    const congregacion_id = document.getElementById('editar-orador-congre').value;
    const discursosStr = document.getElementById('editar-orador-discursos').value;

    const discursos = discursosStr.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d));

    const datosAEnviar = {
        nombre: nombre,
        telefono: telefono,
        congregacion_id: congregacion_id && congregacion_id !== 'NUEVA_CONGREGACION' ? parseInt(congregacion_id) : null,
        discursos: discursos
    };

    try {
        // Añade /api aquí para que coincida con el backend
        const response = await fetch(`/api/oradores/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datosAEnviar)
        });

        if (response.ok) {
            const modalEl = document.getElementById('modalEditarOrador');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            if (typeof cargarOradores === 'function') {
                cargarOradores();
            } else {
                location.reload();
            }
        } else {
            const errorTexto = await response.text();
            console.error("Detalle del error del servidor:", errorTexto);
            alert(`Error del servidor (${response.status}): Revisa la consola (F12).`);
        }
    } catch (error) {
        console.error('Error de red:', error);
        alert('Error de conexión al guardar los cambios.');
    }
}
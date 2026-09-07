document.addEventListener("DOMContentLoaded", () => {
    // Escudo: Si no estamos en la página de planificación, el script no hace nada
    const contenedor = document.getElementById('tablaPlanificacionBody');
    if (!contenedor) return;

    inicializarSelectorAnios();

    const selector = document.getElementById('selectAnioPlan');
    if (selector) {
        selector.addEventListener('change', () => {
            cargarPlanificacion();
        });
    }

    cargarPlanificacion();
});

async function cargarPlanificacion() {
    const selector = document.getElementById('selectAnioPlan');
    const anio = (selector && selector.value) ? selector.value : new Date().getFullYear();

    try {
        let res = await fetch(`/api/planificacion?anio=${anio}`);
        let lista = await res.json();

        if (lista.length === 0) {
            await fetch(`/api/planificacion/generar-anio/${anio}`, { method: 'POST' });
            res = await fetch(`/api/planificacion?anio=${anio}`);
            lista = await res.json();
        }

        const contenedor = document.getElementById('tablaPlanificacionBody');
        if (!contenedor) return;
        contenedor.innerHTML = '';

        let mesAnterior = null;
        const mesesNombres = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ];

        lista.forEach(item => {
            const fechaObj = new Date(item.fecha);
            const mesActual = fechaObj.getMonth();
            const anioActual = fechaObj.getFullYear();

            if (mesActual !== mesAnterior) {
                mesAnterior = mesActual;
                contenedor.innerHTML += `
                    <tr class="table-secondary fw-bold">
                        <td colspan="8" class="text-uppercase text-secondary ps-3" style="letter-spacing: 0.5px; font-size: 0.95rem;">
                            📅 ${mesesNombres[mesActual]} ${anioActual}
                        </td>
                    </tr>
                `;
            }

            const fechaStr = fechaObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });

            let infoOrador = '';
            if (item.es_evento_especial) {
                infoOrador = `<span class="badge bg-danger">${item.texto_evento || 'Evento Especial'}</span>`;
            } else {
                infoOrador = item.orador_nombre || '<span class="text-muted">Por asignar</span>';
            }

            const telefono = item.es_evento_especial ? '-' : (item.orador_telefono || '-');
            const congregacion = item.es_evento_especial ? '-' : (item.orador_congregacion || 'Propia');
            
            const bosquejoTema = item.es_evento_especial 
                ? '<span class="text-muted">-</span>' 
                : (item.numero_bosquejo ? `<strong>${item.numero_bosquejo}</strong> - ${item.bosquejo_tema || ''}` : '<span class="text-muted">-</span>');

            const badgeInv = item.estado_invitacion === 'Enviada' 
                ? `<span class="badge bg-success" style="cursor:pointer;" onclick="event.stopPropagation(); cambiarEstado(${item.id}, 'estado_invitacion', 'No enviada')">Enviada</span>`
                : `<span class="badge bg-warning text-dark" style="cursor:pointer;" onclick="event.stopPropagation(); cambiarEstado(${item.id}, 'estado_invitacion', 'Enviada')">No enviada</span>`;

            const badgeConf = item.estado_confirmacion === 'Confirmado' 
                ? `<span class="badge bg-success" style="cursor:pointer;" onclick="event.stopPropagation(); cambiarEstado(${item.id}, 'estado_confirmacion', 'Pendiente')">Confirmado</span>`
                : `<span class="badge bg-secondary" style="cursor:pointer;" onclick="event.stopPropagation(); cambiarEstado(${item.id}, 'estado_confirmacion', 'Confirmado')">Pendiente</span>`;

            const fechaEnvio = item.fecha_envio_invitacion 
                ? new Date(item.fecha_envio_invitacion).toLocaleDateString('es-ES') 
                : '-';

            contenedor.innerHTML += `
                <tr class="fila-plan" style="cursor: pointer;" onclick="abrirModalEditar(${item.id})">
                    <td class="fw-bold ps-4">${fechaStr}</td>
                    <td>${infoOrador}</td>
                    <td>${telefono}</td>
                    <td>${congregacion}</td>
                    <td>${bosquejoTema}</td>
                    <td>${badgeInv}</td>
                    <td>${badgeConf}</td>
                    <td>${fechaEnvio}</td>
                </tr>
            `;
        });
    } catch (err) {
        console.error("Error al cargar planificación:", err);
    }
}

async function cambiarEstado(id, campo, nuevoEstado) {
    const payload = {};
    payload[campo] = nuevoEstado;
    await fetch(`/api/planificacion/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    cargarPlanificacion();
}

function inicializarSelectorAnios() {
    const select = document.getElementById('selectAnioPlan');
    if (!select) return;

    const anioActual = new Date().getFullYear();
    select.innerHTML = '';

    for (let anio = 2025; anio <= anioActual + 1; anio++) {
        const option = document.createElement('option');
        option.value = anio;
        option.textContent = anio;
        if (anio === anioActual) option.selected = true;
        select.appendChild(option);
    }
}

// --- LÓGICA DEL MODAL DE EDICIÓN MANUAL EN PLANIFICACIÓN ---

let oradoresCargadosModal = [];

// Helper para ignorar tildes y mayúsculas/minúsculas
function normalizarTexto(texto) {
    return (texto || '')
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

// Obtener el título automáticamente al cambiar el número de discurso en el modal
document.addEventListener('DOMContentLoaded', () => {
    const selectNumModal = document.getElementById('select-bosquejo-modal');
    if (selectNumModal) {
        selectNumModal.addEventListener('change', async (e) => {
            const num = e.target.value;
            const inputTitulo = document.getElementById('input-bosquejo-titulo');
            
            if (!num) {
                if (inputTitulo) inputTitulo.value = '';
                return;
            }

            try {
                const res = await fetch(`/api/bosquejos/${num}`);
                const data = await res.json();
                if (inputTitulo) inputTitulo.value = data.titulo || '';
            } catch (err) {
                console.error("Error al obtener el bosquejo:", err);
            }
        });
    }
});


// Abrir modal y precargar datos con las columnas correctas
async function abrirModalEditar(fechaId) {
    document.getElementById('edit-fecha-id').value = fechaId;
    
    try {
        if (oradoresCargadosModal.length === 0) {
            const res = await fetch('/api/oradores');
            oradoresCargadosModal = await res.json();
        }

        actualizarDatalistModal('');

        let nombreOrador = '';
        let telefonoOrador = '';
        let congregacionOrador = '';
        let bosquejoNumActual = null;
        let esEventoEspecial = false;
        let textoEventoEspecial = '';

        // Buscar la fila de manera robusta
        let fila = null;
        const filasTabla = document.querySelectorAll('#tablaPlanificacionBody tr');
        for (let f of filasTabla) {
            const onclickAttr = f.getAttribute('onclick') || '';
            if (onclickAttr.includes(`abrirModalEditar(${fechaId})`) || onclickAttr.includes(`abrirModalEditar('${fechaId}')`) || onclickAttr.includes(`abrirModalEditar("${fechaId}")`)) {
                fila = f;
                break;
            }
        }

        if (fila) {
            // Comprobar si el texto del orador contiene un badge rojo de evento especial
            const celdaOrador = fila.querySelectorAll('td')[1];
            if (celdaOrador && celdaOrador.querySelector('.badge.bg-danger')) {
                esEventoEspecial = true;
                textoEventoEspecial = celdaOrador.querySelector('.badge.bg-danger').innerText.trim();
            }

            const celdas = fila.querySelectorAll('td');
            celdas.forEach((celda, index) => {
                const texto = celda.innerText.trim();
                if (!texto || texto === '-') return;

                if (texto.match(/\d{2}\/\d{2}\/\d{4}|\d{4}-\d{2}-\d{2}/)) return;

                const soloNums = texto.replace(/\D/g, '');
                if (soloNums.length >= 7 && soloNums.length <= 15) {
                    telefonoOrador = texto;
                    return;
                }

                if (texto.match(/^\d+\s*-/) || (index >= celdas.length - 2 && !isNaN(texto))) {
                    return;
                }

                if (!nombreOrador && index <= 2 && !texto.includes(' - ') && !esEventoEspecial) {
                    nombreOrador = texto;
                    return;
                }

                if (nombreOrador && texto !== nombreOrador && texto !== telefonoOrador && !congregacionOrador) {
                    congregacionOrador = texto;
                }
            });

            if (fila.dataset.orador) nombreOrador = fila.dataset.orador;
            if (fila.dataset.telefono) telefonoOrador = fila.dataset.telefono;
            if (fila.dataset.congregacion) congregacionOrador = fila.dataset.congregacion;
            bosquejoNumActual = fila.dataset.bosquejo || null;
        }

        // Controlar los elementos del DOM para el evento especial en el modal
        const checkEspecial = document.getElementById('check-evento-especial');
        const inputTextoEspecial = document.getElementById('input-texto-evento');
        
        if (checkEspecial) {
            checkEspecial.checked = esEventoEspecial;
            toggleCamposEventoEspecial(); // Muestra/oculta los bloques visuales
        }
        if (inputTextoEspecial) {
            inputTextoEspecial.value = textoEventoEspecial;
        }

        if (telefonoOrador === '-' || telefonoOrador === 'undefined') telefonoOrador = '';
        if (congregacionOrador === '-' || congregacionOrador === 'undefined') congregacionOrador = '';

        document.getElementById('input-orador-nombre').value = nombreOrador;
        document.getElementById('input-telefono').value = telefonoOrador;
        document.getElementById('input-congregacion').value = congregacionOrador;

        await alSeleccionarOradorModal(nombreOrador, bosquejoNumActual, congregacionOrador);

        var myModal = new bootstrap.Modal(document.getElementById('modalEditarPlan'));
        myModal.show();
    } catch (err) {
        console.error("Error al abrir el modal:", err);
        alert("No se pudieron cargar los datos.");
    }
}


async function alSeleccionarOradorModal(valorIngresado, bosquejoSeleccionadoNum = null, congregacionFila = '') {
    actualizarDatalistModal(valorIngresado);

    const selectNum = document.getElementById('select-bosquejo-modal');
    const inputTitulo = document.getElementById('input-bosquejo-titulo');
    const inputTelefono = document.getElementById('input-telefono');
    const inputCongregacion = document.getElementById('input-congregacion');
    
    if (!selectNum) return;

    // Asignar de inmediato la congregación de la fila si existe
    if (congregacionFila && congregacionFila !== '-' && congregacionFila.trim() !== '') {
        inputCongregacion.value = congregacionFila;
    }

    const valorNorm = normalizarTexto(valorIngresado);
    const oradorEncontrado = oradoresCargadosModal.find(o => normalizarTexto(o.nombre) === valorNorm);

    if (!oradorEncontrado) {
        selectNum.innerHTML = '<option value="">Selecciona un bosquejo...</option>';
        if (inputTitulo) inputTitulo.value = '';
        inputTelefono.value = '';
        inputCongregacion.value = '';
        return;
    }

    // Actualizar teléfono
    inputTelefono.value = (oradorEncontrado.telefono && oradorEncontrado.telefono !== '-') ? oradorEncontrado.telefono : '';

    // Actualizar congregación si la ficha oficial la tiene y el campo estaba vacío
    const congreOficial = oradorEncontrado.congregacion?.nombre || 
                          oradorEncontrado.congregacion || 
                          oradorEncontrado.congregacion_nombre || 
                          oradorEncontrado.nombre_congregacion || '';

    if (congreOficial && congreOficial !== '-' && congreOficial.trim() !== '') {
        inputCongregacion.value = congreOficial;
    } else if (!inputCongregacion.value && congregacionFila) {
        inputCongregacion.value = congregacionFila;
    }

    // Cargar los discursos del orador
    const discursos = oradorEncontrado.discursos || [];
    if (discursos.length === 0) {
        selectNum.innerHTML = '<option value="">El orador no tiene discursos asignados</option>';
        if (inputTitulo) inputTitulo.value = '';
        return;
    }

    selectNum.innerHTML = '<option value="">Selecciona un bosquejo...</option>' +
        discursos.map(d => {
            const num = d.numero_discurso || d.numero || d;
            return `<option value="${num}">Bosquejo Nº ${num}</option>`;
        }).join('');

    if (bosquejoSeleccionadoNum) {
        selectNum.value = bosquejoSeleccionadoNum;
        try {
            const res = await fetch(`/api/bosquejos/${bosquejoSeleccionadoNum}`);
            const data = await res.json();
            if (inputTitulo) inputTitulo.value = data.titulo || '';
        } catch (err) {
            console.error("Error al obtener el bosquejo:", err);
        }
    } else {
        if (inputTitulo) inputTitulo.value = '';
    }
}

// Renderizar solo las opciones que coinciden con la búsqueda
function actualizarDatalistModal(filtro) {
    const datalist = document.getElementById('listaOradoresDatalist');
    if (!datalist) return;

    const filtroNorm = normalizarTexto(filtro);
    const filtrados = filtroNorm === '' 
        ? oradoresCargadosModal 
        : oradoresCargadosModal.filter(o => normalizarTexto(o.nombre).includes(filtroNorm));

    datalist.innerHTML = filtrados
        .map(o => `<option value="${o.nombre}">`)
        .join('');
}

// Función ejecutada al escribir o seleccionar el orador
 async function alSeleccionarOradorModal(valorIngresado, bosquejoSeleccionadoNum = null, congregacionFila = '') {
    actualizarDatalistModal(valorIngresado);

    const selectNum = document.getElementById('select-bosquejo-modal');
    const inputTitulo = document.getElementById('input-bosquejo-titulo');
    const inputTelefono = document.getElementById('input-telefono');
    const inputCongregacion = document.getElementById('input-congregacion');
    
    if (!selectNum) return;

    const valorNorm = normalizarTexto(valorIngresado);
    const oradorEncontrado = oradoresCargadosModal.find(o => normalizarTexto(o.nombre) === valorNorm);

    // Si no se encuentra un orador válido en la lista, limpiamos los campos
    if (!oradorEncontrado) {
        selectNum.innerHTML = '<option value="">Selecciona un bosquejo...</option>';
        if (inputTitulo) inputTitulo.value = '';
        inputTelefono.value = '';
        inputCongregacion.value = '';
        return;
    }

    // Actualizar siempre el teléfono con el del nuevo orador seleccionado (o dejarlo vacío si no tiene)
    inputTelefono.value = (oradorEncontrado.telefono && oradorEncontrado.telefono !== '-') ? oradorEncontrado.telefono : '';

    // Actualizar la congregación: Priorizar la de la ficha oficial del orador, luego la de la fila, o vaciar
    const congreOficial = oradorEncontrado.congregacion?.nombre || 
                          oradorEncontrado.congregacion || 
                          oradorEncontrado.congregacion_nombre || 
                          oradorEncontrado.nombre_congregacion || '';

    if (congreOficial && congreOficial !== '-') {
        inputCongregacion.value = congreOficial;
    } else if (congregacionFila && congregacionFila !== '-') {
        inputCongregacion.value = congregacionFila;
    } else {
        inputCongregacion.value = '';
    }

    // Cargar los discursos del nuevo orador seleccionado
    const discursos = oradorEncontrado.discursos || [];
    if (discursos.length === 0) {
        selectNum.innerHTML = '<option value="">El orador no tiene discursos asignados</option>';
        if (inputTitulo) inputTitulo.value = '';
        return;
    }

    selectNum.innerHTML = '<option value="">Selecciona un bosquejo...</option>' +
        discursos.map(d => {
            const num = d.numero_discurso || d.numero || d;
            return `<option value="${num}">Bosquejo Nº ${num}</option>`;
        }).join('');

    // Si ya tenía un bosquejo asignado previamente (al abrir el modal), lo seleccionamos
    if (bosquejoSeleccionadoNum) {
        selectNum.value = bosquejoSeleccionadoNum;
        try {
            const res = await fetch(`/api/bosquejos/${bosquejoSeleccionadoNum}`);
            const data = await res.json();
            if (inputTitulo) inputTitulo.value = data.titulo || '';
        } catch (err) {
            console.error("Error al obtener el bosquejo:", err);
        }
    } else {
        if (inputTitulo) inputTitulo.value = '';
    }
}

// Guardar cambios en la planificación
async function guardarAsignacionManual() {
    const fechaId = document.getElementById('edit-fecha-id').value;
    const nombreOrador = document.getElementById('input-orador-nombre')?.value.trim();
    const telefono = document.getElementById('input-telefono')?.value;
    const congregacion = document.getElementById('input-congregacion')?.value;
    
    const valorNorm = normalizarTexto(nombreOrador);
    const oradorEncontrado = oradoresCargadosModal.find(o => normalizarTexto(o.nombre) === valorNorm);
    const oradorId = oradorEncontrado ? oradorEncontrado.id : null;

    const selectBosquejo = document.getElementById('select-bosquejo-modal');
    const bosquejoNumero = selectBosquejo?.value ? parseInt(selectBosquejo.value) : null;
    const bosquejoTitulo = document.getElementById('input-bosquejo-titulo')?.value || '';

    if (!nombreOrador || !bosquejoNumero) {
        alert("Por favor selecciona un orador y un número de bosquejo.");
        return;
    }

    const payload = {
        orador_id: oradorId,
        nombre_orador: nombreOrador,
        telefono: telefono,
        congregacion: congregacion,
        bosquejo_numero: bosquejoNumero,
        bosquejo_titulo: bosquejoTitulo
    };

    try {
        // Cambiado a POST para evitar el error 405 Method Not Allowed si el servidor lo requiere
        const response = await fetch(`/api/planificacion/${fechaId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (response.ok) {
            location.reload();
        } else {
            alert("Error: " + (result.detalle || result.error || "No se pudo actualizar"));
        }
    } catch (err) {
        console.error("Error al guardar:", err);
        alert("Hubo un error de conexión al guardar.");
    }
}

async function guardarAsignacionManual() {
    const fechaId = document.getElementById('edit-fecha-id').value;
    const esEspecial = document.getElementById('check-evento-especial')?.checked || false;
    const textoEvento = document.getElementById('input-texto-evento')?.value.trim() || '';

    let payload = {};

    if (esEspecial) {
        if (!textoEvento) {
            alert("Por favor, escribe el nombre del evento especial.");
            return;
        }
        payload = {
            es_evento_especial: true,
            texto_evento: textoEvento,
            id_orador: null,
            numero_bosquejo: null
        };
    } else {
        const nombreOrador = document.getElementById('input-orador-nombre')?.value.trim();
        const valorNorm = normalizarTexto(nombreOrador);
        const oradorEncontrado = oradoresCargadosModal.find(o => normalizarTexto(o.nombre) === valorNorm);
        const oradorId = oradorEncontrado ? oradorEncontrado.id : null;

        const selectBosquejo = document.getElementById('select-bosquejo-modal');
        const bosquejoNumero = selectBosquejo?.value ? parseInt(selectBosquejo.value) : null;

        if (!oradorId || !bosquejoNumero) {
            alert("Por favor selecciona un orador válido de la lista y un número de bosquejo.");
            return;
        }

        payload = {
            es_evento_especial: false,
            texto_evento: null,
            id_orador: oradorId,
            numero_bosquejo: bosquejoNumero
        };
    }

    try {
        const response = await fetch(`/api/planificacion/${fechaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            // Cerrar modal y limpiar
            const modalElement = document.getElementById('modalEditarPlan');
            if (modalElement) {
                const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
                modalInstance.hide();
                modalElement.classList.remove('show');
                modalElement.style.display = 'none';
            }
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');

            cargarPlanificacion();
        } else {
            const result = await response.json();
            alert("Error al actualizar: " + (result.detail || "No se pudo guardar"));
        }
    } catch (err) {
        console.error("Error de red al guardar:", err);
        alert("Hubo un error de conexión al guardar.");
    }
}

async function borrarAsignacion() {
    if (!confirm("¿Estás seguro de que quieres dejar esta fecha sin asignar?")) {
        return;
    }

    const fechaId = document.getElementById('edit-fecha-id').value;

    // Al enviar null en ambos campos, tu backend los limpia automáticamente
    const payload = {
        id_orador: null,
        numero_bosquejo: null
    };

    try {
        const response = await fetch(`/api/planificacion/${fechaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            // Cerrar el modal suavemente
            const modalElement = document.getElementById('modalAsignar') || document.querySelector('.modal');
            if (modalElement) {
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) modalInstance.hide();
                else modalElement.style.display = 'none';
            }

            // Recargar la tabla sin perder la pestaña
            if (typeof cargarPlanificacion === 'function') {
                cargarPlanificacion();
            } else if (typeof obtenerPlanificacion === 'function') {
                obtenerPlanificacion();
            } else {
                location.reload();
            }
        } else {
            alert("No se pudo vaciar la fecha.");
        }
    } catch (err) {
        console.error("Error de red al borrar:", err);
        alert("Hubo un error de conexión al borrar la asignación.");
    }
}

function toggleCamposEventoEspecial() {
    const esEspecial = document.getElementById('check-evento-especial').checked;
    const containerTexto = document.getElementById('container-texto-evento');
    const bloqueNormales = document.getElementById('bloque-campos-normales');

    if (esEspecial) {
        containerTexto.style.display = 'block';
        bloqueNormales.style.display = 'none'; // Opcional: oculta los campos de oradores si no se usan
    } else {
        containerTexto.style.display = 'none';
        bloqueNormales.style.display = 'block';
    }
}
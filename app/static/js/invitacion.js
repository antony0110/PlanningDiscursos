let oradoresCargados = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarOradoresDirecto();

    // Obtener el título automáticamente al cambiar el número de discurso
    const selectNum = document.getElementById('pdfNumDiscurso');
    if (selectNum) {
        selectNum.addEventListener('change', async (e) => {
            const num = e.target.value;
            const inputTitulo = document.getElementById('pdfTituloDiscurso');
            
            if (!num) {
                if (inputTitulo) inputTitulo.value = '';
                // Limpiar aviso de discurso si no hay selección
                const avisoDiv = document.getElementById('avisoAntiguedadDiscurso');
                if (avisoDiv) avisoDiv.style.display = 'none';
                return;
            }

            // Llamamos a la validación del discurso al cambiar de número
            await verificarAntiguedadDiscurso();

            try {
                const res = await fetch(`/api/bosquejos/${num}`);
                const data = await res.json();
                if (inputTitulo) inputTitulo.value = data.titulo || '';
            } catch (err) {
                console.error("Error al obtener el bosquejo:", err);
            }
        });
    }

    // ⭐ CORRECCIÓN: Listener para limpiar automáticamente al cambiar o escribir el orador
    const inputOradorElem = document.getElementById('pdfOradorNombre');
    if (inputOradorElem) {
        inputOradorElem.addEventListener('input', function() {
            // 1. Resetear el selector de números de discurso a su estado inicial
            const selectBosquejo = document.getElementById('pdfNumDiscurso');
            if (selectBosquejo) {
                selectBosquejo.innerHTML = '<option value="">Selecciona un bosquejo...</option>';
                selectBosquejo.value = '';
            }

            // 2. Vaciar el título del discurso que se autocompleta
            const inputTitulo = document.getElementById('pdfTituloDiscurso');
            if (inputTitulo) {
                inputTitulo.value = '';
            }

            // 3. Ocultar y limpiar el cuadro de advertencia del discurso
            const avisoBosquejoDiv = document.getElementById('avisoAntiguedadDiscurso');
            if (avisoBosquejoDiv) {
                avisoBosquejoDiv.innerHTML = '';
                avisoBosquejoDiv.style.display = 'none';
            }

            // 4. Ocultar y limpiar el cuadro de advertencia del orador
            const avisoOradorDiv = document.getElementById('avisoAntiguedadOrador');
            if (avisoOradorDiv) {
                avisoOradorDiv.innerHTML = '';
                avisoOradorDiv.style.display = 'none';
            }
        });
    }
});

// Helper para ignorar tildes y mayúsculas/minúsculas
function normalizarTexto(texto) {
    return (texto || '')
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

// 1. Cargar oradores desde la API
async function cargarOradoresDirecto() {
    const datalist = document.getElementById('listaOradoresDatalist');
    const inputOrador = document.getElementById('pdfOradorNombre');
    if (!datalist) return;

    try {
        const res = await fetch('/api/oradores');
        oradoresCargados = await res.json();

        actualizarDatalist('');

        if (inputOrador) inputOrador.placeholder = "Escribe para buscar...";
    } catch (err) {
        console.error("Error al cargar oradores:", err);
        if (inputOrador) inputOrador.placeholder = "Error al cargar oradores";
    }
}

// 2. Renderizar solo las opciones que coinciden con la búsqueda
function actualizarDatalist(filtro) {
    const datalist = document.getElementById('listaOradoresDatalist');
    if (!datalist) return;

    const filtroNorm = normalizarTexto(filtro);

    const filtrados = filtroNorm === '' 
        ? oradoresCargados 
        : oradoresCargados.filter(o => normalizarTexto(o.nombre).includes(filtroNorm));

    datalist.innerHTML = filtrados
        .map(o => `<option value="${o.nombre}">`)
        .join('');
}

// 3. Función ejecutada cada vez que el usuario escribe un carácter
async function alSeleccionarOrador(valorIngresado) {
    // Re-filtrar el desplegable dinámicamente
    actualizarDatalist(valorIngresado);

    const selectNum = document.getElementById('pdfNumDiscurso');
    const inputTitulo = document.getElementById('pdfTituloDiscurso');
    if (!selectNum) return;

    // Verificar si coincide exactamente con algún orador de la lista
    const valorNorm = normalizarTexto(valorIngresado);
    const oradorEncontrado = oradoresCargados.find(o => normalizarTexto(o.nombre) === valorNorm);

    if (!oradorEncontrado) {
        selectNum.innerHTML = '<option value="">Selecciona un bosquejo...</option>';
        if (inputTitulo) inputTitulo.value = '';
        
        // Ocultar el aviso del orador si aún no se ha seleccionado uno válido
        const avisoOradorDiv = document.getElementById('avisoAntiguedadOrador');
        if (avisoOradorDiv) avisoOradorDiv.style.display = 'none';
        return;
    }

    // Validación de la antigüedad de los 2 años del orador
    await verificarAntiguedadOrador(oradorEncontrado.nombre);

    // Cargar discursos del orador seleccionado
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
}

// 4. Enviar WhatsApp Directo con la plantilla personalizada
function enviarWhatsAppDirecto() {
    const oradorNombre = document.getElementById('pdfOradorNombre')?.value;
    const numDiscurso = document.getElementById('pdfNumDiscurso')?.value;
    const fechaRaw = document.getElementById('pdfFecha')?.value;
    const fechaTexto = typeof formatearFechaEspanol === 'function' ? formatearFechaEspanol(fechaRaw) : fechaRaw;

    if (!oradorNombre || !numDiscurso) {
        alert("Por favor selecciona un orador y un número de discurso.");
        return;
    }

    const valorNorm = normalizarTexto(oradorNombre);
    const orador = oradoresCargados.find(o => normalizarTexto(o.nombre) === valorNorm);
    const telefonoLimpio = orador?.telefono ? String(orador.telefono).replace(/\D/g, '') : '';

    const primerNombre = oradorNombre.trim().split(' ')[0];

    const mensaje = `Hola buenos días ${primerNombre} :\n\n` +
                    `Soy Antony, de la congregación de Algemesí. Te escribo porque me gustaría invitarte a dar un discurso en nuestra congregación el día ${fechaTexto || '[Fecha]'}\n\n` +
                    `Te adjunto la invitación con toda la información. ¿Podrías confirmarme cuanto antes si vas a poder venir?\n\n` +
                    `Muchas gracias.\n` +
                    `¡Un abrazo!`;

    let telefonoFinal = telefonoLimpio;
    if (telefonoLimpio.length === 9) {
        telefonoFinal = `34${telefonoLimpio}`;
    }

    const url = `https://api.whatsapp.com/send?phone=${telefonoFinal}&text=${encodeURIComponent(mensaje)}`;
    window.open(url, '_blank');
}

// 5. Descargar PDF
function generarPDFDirecto() {
    const oradorNombre = document.getElementById('pdfOradorNombre')?.value;
    const numDiscurso = document.getElementById('pdfNumDiscurso')?.value;
    const tituloDiscurso = document.getElementById('pdfTituloDiscurso')?.value || '';
    const fechaRaw = document.getElementById('pdfFecha')?.value;
    const fechaTexto = typeof formatearFechaEspanol === 'function' ? formatearFechaEspanol(fechaRaw) : fechaRaw;

    if (!oradorNombre || !numDiscurso) {
        alert("Completa al menos el nombre del orador y el número de discurso.");
        return;
    }

    const url = `/api/invitacion/pdf?orador_nombre=${encodeURIComponent(oradorNombre)}&numero_discurso=${encodeURIComponent(numDiscurso)}&titulo_discurso=${encodeURIComponent(tituloDiscurso)}&fecha_texto=${encodeURIComponent(fechaTexto)}`;
    window.open(url, '_blank');
}

// 6. Validación del DISCURSO (< 1 año O asignado a futuro)
async function verificarAntiguedadDiscurso() {
    const selectBosquejo = document.getElementById('pdfNumDiscurso');
    const avisoDiv = document.getElementById('avisoAntiguedadDiscurso');
    if (!avisoDiv || !selectBosquejo) return;
    
    const valorSeleccionado = selectBosquejo.value;
    if (!valorSeleccionado) {
        avisoDiv.style.display = 'none';
        return;
    }

    const numeroBosquejo = valorSeleccionado.replace(/\D/g, '');
    if (!numeroBosquejo) {
        avisoDiv.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/api/historico/bosquejo/${numeroBosquejo}`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.encontrado_reciente && data.ultima_fecha) {
            const partes = data.ultima_fecha.split('-');
            const fechaFormateada = `${partes[2]}/${partes[1]}/${partes[0]}`;
            
            avisoDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-warning"></i> ⚠️ Este discurso se ha hecho hace menos de un año (última vez el <strong>${fechaFormateada}</strong>).`;
            avisoDiv.className = "form-text text-danger fw-semibold mt-1";
            avisoDiv.style.display = "block";
        } else if (data.asignado_futuro && data.fecha_futura) {
            const partes = data.fecha_futura.split('-');
            const fechaFuturaFormateada = `${partes[2]}/${partes[1]}/${partes[0]}`;
            
            avisoDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-warning"></i> ⚠️ Este discurso ya está programado a futuro en el panel (el <strong>${fechaFuturaFormateada}</strong>).`;
            avisoDiv.className = "form-text text-warning fw-semibold mt-1";
            avisoDiv.style.display = "block";
        } else {
            avisoDiv.style.display = "none";
        }
    } catch (error) {
        console.error("Error al comprobar la antigüedad del discurso:", error);
        avisoDiv.style.display = "none";
    }
}

// 7. Validación del ORADOR
async function verificarAntiguedadOrador(nombreOrador) {
    const avisoOradorDiv = document.getElementById('avisoAntiguedadOrador'); 
    if (!avisoOradorDiv) return;

    const valorNorm = normalizarTexto(nombreOrador);
    const oradorEncontrado = oradoresCargados.find(o => normalizarTexto(o.nombre) === valorNorm);

    if (!oradorEncontrado) {
        avisoOradorDiv.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/api/historico/orador?nombre=${encodeURIComponent(nombreOrador)}`);
        if (!response.ok) return;

        const data = await response.json();
        
        if (data.encontrado_en_rango && data.ultima_fecha) {
            const partes = data.ultima_fecha.split('-');
            const fechaFormateada = `${partes[2]}/${partes[1]}/${partes[0]}`;
            
            avisoOradorDiv.innerHTML = `<i class="bi bi-info-circle-fill text-info"></i> Este orador vino recientemente (última vez el <strong>${fechaFormateada}</strong>).`;
            avisoOradorDiv.className = "form-text text-info fw-semibold mt-1";
            avisoOradorDiv.style.display = "block";
        } else {
            avisoOradorDiv.style.display = "none";
        }
    } catch (error) {
        console.error("Error al comprobar la antigüedad del orador:", error);
        avisoOradorDiv.style.display = "none";
    }
}
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
function alSeleccionarOrador(valorIngresado) {
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
        return;
    }

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

    // Extraemos solo el primer nombre (ej: "Enrique") para un saludo más cercano
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
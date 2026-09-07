let listaOradoresGlobal = [];

document.addEventListener('DOMContentLoaded', () => {
    // 1. Asignar el próximo domingo por defecto en los inputs de fecha
    const hoy = new Date();
    const proximoDomingo = new Date(hoy.setDate(hoy.getDate() + ((7 - hoy.getDay()) % 7)));
    const fechaDefault = proximoDomingo.toISOString().split('T')[0];
    
    const inputFechaInv = document.getElementById('fechaInvitacion');
    const inputPdfFecha = document.getElementById('pdfFecha');
    
    if (inputFechaInv) inputFechaInv.value = fechaDefault;
    if (inputPdfFecha) inputPdfFecha.value = fechaDefault;

    // 2. Mostrar por defecto la sección de discursantes al arrancar
    cambiarSeccion('discursantes');

    cargarCongregaciones();
    filtrarPorCongregacion();
});


function cambiarSeccion(seccion) {
    ['discursantes', 'invitacion', 'planificacion', 'historico'].forEach(sec => {
        const elSec = document.getElementById('sec-' + sec);
        const elBtn = document.getElementById('btn-' + sec);
        if (elSec) elSec.style.display = (sec === seccion) ? 'block' : 'none';
        if (elBtn) elBtn.classList.toggle('active', sec === seccion);
    });

    // Si se abre el histórico, lanzamos su función de carga de datos
    if (seccion === 'historico' && typeof cargarHistorico === 'function') {
        cargarHistorico();
    }
}
// Cargar congregaciones en el desplegable de filtro
async function cargarCongregaciones() {
    try {
        const res = await fetch('/api/congregaciones');
        const congregaciones = await res.json();
        const select = document.getElementById('selectCongregacion');
        if (!select) return;
        
        select.innerHTML = '<option value="">Todas las congregaciones</option>';
        congregaciones.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.nombre}</option>`;
        });
    } catch (err) {
        console.error("Error al cargar congregaciones:", err);
    }
}

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

    tbody.innerHTML = oradores.map(o => {
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
                <button onclick="abrirModalEditar(${o.id})" class="btn btn-sm btn-outline-primary me-1" title="Modificar orador">
                    <i class="bi bi-pencil-fill"></i>
                </button>
                <button onclick="eliminarOrador(${o.id})" class="btn btn-sm btn-outline-danger" title="Eliminar orador">
                    <i class="bi bi-trash-fill"></i>
                </button>
            </td>
        </tr>`;
    }).join('');
}

// Búsquedas y filtros de la tabla
async function buscarPorDiscurso() {
    const num = document.getElementById('numDiscurso')?.value;
    if (!num) return;
    try {
        const res = await fetch(`/api/oradores/buscar-por-discurso?numero=${num}`);
        const data = await res.json();
        renderTabla(data);
    } catch (err) {
        console.error("Error al buscar por discurso:", err);
    }
}

async function filtrarPorCongregacion() {
    const select = document.getElementById('selectCongregacion');
    const id = select ? select.value : '';
    const url = id ? `/api/oradores?congregacion_id=${id}` : '/api/oradores';
    try {
        const res = await fetch(url);
        const data = await res.json();
        renderTabla(data);
    } catch (err) {
        console.error("Error al filtrar por congregación:", err);
    }
}

// Helper global para dar formato a las fechas
function formatearFechaEspanol(fechaStr) {
    if (!fechaStr) return "____";
    const partes = fechaStr.split('-');
    if (partes.length !== 3) return fechaStr;
    const fecha = new Date(partes[0], partes[1] - 1, partes[2]);
    return fecha.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
}

//LOGIN

// Mostrar u ocultar la pantalla de la aplicación según el estado de la sesión
function cambiarVistaSesion(sesionActiva, rol = null) {
    const loginScreen = document.getElementById('login-screen');
    const appContainer = document.getElementById('app-container');

    if (sesionActiva) {
        if (loginScreen) {
            loginScreen.classList.add('d-none');
            loginScreen.style.display = 'none';
        }
        if (appContainer) {
            appContainer.classList.remove('d-none');
            appContainer.style.display = 'block';
        }
        if (rol === 'invitado') {
            console.log("Modo Invitado: Solo lectura activado");
        }
    } else {
        if (loginScreen) {
            loginScreen.classList.remove('d-none');
            loginScreen.style.display = 'flex';
        }
        if (appContainer) {
            appContainer.classList.add('d-none');
            appContainer.style.display = 'none';
        }
    }
}

// LOGIN
async function ejecutarLogin() {
    const usuario = document.getElementById('login-user').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const errorDiv = document.getElementById('login-error');

    errorDiv.style.display = 'none';
    errorDiv.textContent = '';

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({
                username: usuario,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            const rolAsignado = data.rol || 'admin';
            localStorage.setItem('usuario', data.username || usuario);
            localStorage.setItem('rol', rolAsignado);
            localStorage.setItem('sesion_activa', 'true');
            
            cambiarVistaSesion(true, rolAsignado);
            console.log("¡Login exitoso! Entrando a la aplicación...");
        } else {
            let mensajeError = "Usuario o contraseña incorrectos.";
            if (data.detail) {
                if (typeof data.detail === 'string') {
                    mensajeError = data.detail;
                } else if (Array.isArray(data.detail)) {
                    mensajeError = data.detail.map(err => err.msg).join(', ');
                }
            }
            
            errorDiv.style.display = 'block';
            errorDiv.textContent = mensajeError;
        }
    } catch (error) {
        console.error("Error en la petición de login:", error);
        errorDiv.style.display = 'block';
        errorDiv.textContent = "Error de conexión con el servidor.";
    }
}

// Ver/Ocultar contraseña
function alternarVisibilidadPassword() {
    const inputPass = document.getElementById('login-password');
    const iconoOjo = document.getElementById('iconoOjo');
    
    if (inputPass.type === "password") {
        inputPass.type = "text";
        iconoOjo.classList.remove("bi-eye");
        iconoOjo.classList.add("bi-eye-slash");
    } else {
        inputPass.type = "password";
        iconoOjo.classList.remove("bi-eye-slash");
        iconoOjo.classList.add("bi-eye");
    }
}

// Cerrar sesión
function cerrarSesion() {
    localStorage.removeItem('sesion_activa');
    localStorage.removeItem('usuario');
    localStorage.removeItem('rol');
    location.reload();
}

// Único listener al cargar la página
document.addEventListener("DOMContentLoaded", () => {
    const usuario = localStorage.getItem('usuario');
    const sesionActiva = localStorage.getItem('sesion_activa');
    const rol = localStorage.getItem('rol');
    
    if (usuario && sesionActiva === 'true') {
        cambiarVistaSesion(true, rol);
    } else {
        cambiarVistaSesion(false);
    }
});
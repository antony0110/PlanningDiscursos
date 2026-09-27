// static/js/auth.js

// GESTIÓN DE VISTA DE SESIÓN
function cambiarVistaSesion(sesionActiva, rol = null) {
    const loginScreen = document.getElementById('login-screen');
    const registerScreen = document.getElementById('register-screen');
    const appContainer = document.getElementById('app-container');
   
    if (sesionActiva) {
        // Ocultar pantallas de autenticación
        if (loginScreen) {
            loginScreen.classList.add('d-none');
            loginScreen.style.display = 'none';
        }
        if (registerScreen) {
            registerScreen.classList.add('d-none');
            registerScreen.style.display = 'none';
        }
        // Mostrar la aplicación principal
        if (appContainer) {
            appContainer.classList.remove('d-none');
            appContainer.style.display = 'block';
        }
        
        // Pintar datos en las esquinas al mostrar la app
        actualizarInfoUI();
    } else {
        // Mostrar el login por defecto y ocultar la app
        if (loginScreen) {
            loginScreen.classList.remove('d-none');
            loginScreen.style.display = 'flex';
        }
        if (registerScreen) {
            registerScreen.classList.add('d-none');
            registerScreen.style.display = 'none';
        }
        if (appContainer) {
            appContainer.classList.add('d-none');
            appContainer.style.display = 'none';
        }
    }
}

// FUNCIÓN AUXILIAR PARA PINTAR USUARIO Y CONGREGACIÓN EN LAS ESQUINAS
function actualizarInfoUI() {
    const username = localStorage.getItem('usuario');
    const congregacion = localStorage.getItem('congregacion');

    const userElement = document.getElementById('display-username');
    const congElement = document.getElementById('display-congregation');

    if (userElement && username) {
        userElement.textContent = username;
    }
    if (congElement && congregacion) {
        congElement.textContent = congregacion;
    }
}

// EJECUTAR LOGIN Y GUARDAR CONGREGACIÓN
async function ejecutarLogin() {
    const usuario = document.getElementById('login-user').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const errorDiv = document.getElementById('login-error');

    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usuario, password: password })
        });

        const data = await response.json();

        if (response.ok) {
            const rolAsignado = data.rol || 'admin';
            localStorage.setItem('usuario', data.username || usuario);
            localStorage.setItem('rol', rolAsignado);
            
            // Guardamos el nombre de la congregación y el ID si vienen en la respuesta
            if (data.congregacion) {
                localStorage.setItem('congregacion', data.congregacion);
            }
            if (data.congregacion_id) {
                localStorage.setItem('congregacion_id', data.congregacion_id);
            }
            
            localStorage.setItem('sesion_activa', 'true');
            
            cambiarVistaSesion(true, rolAsignado);
            if (typeof cargarCongregaciones === 'function') cargarCongregaciones();
            if (typeof filtrarPorCongregacion === 'function') filtrarPorCongregacion();
        } else {
            let mensajeError = data.detail || "Usuario o contraseña incorrectos.";
            if (errorDiv) {
                errorDiv.style.display = 'block';
                errorDiv.textContent = typeof mensajeError === 'string' ? mensajeError : JSON.stringify(mensajeError);
            }
        }
    } catch (error) {
        console.error("Error en la petición de login:", error);
        if (errorDiv) {
            errorDiv.style.display = 'block';
            errorDiv.textContent = "Error de conexión con el servidor.";
        }
    }
}

// REGISTRO INTELIGENTE
async function ejecutarRegistro() {
    const usuarioInput = document.getElementById('reg-user');
    const passwordInput = document.getElementById('reg-password');
    const congregacionInput = document.getElementById('reg-congregacion');
    const errorDiv = document.getElementById('reg-error');

    const usuario = usuarioInput ? usuarioInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';
    const congregacionId = congregacionInput ? congregacionInput.value.trim() : '';

    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }

    try {
        const response = await fetch('/api/auth/crear-usuario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: usuario,
                password: password,
                rol: "admin",
                congregacion_id: congregacionId ? parseInt(congregacionId) : null
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert("¡Usuario creado correctamente! Ya puedes iniciar sesión.");
            if (usuarioInput) usuarioInput.value = '';
            if (passwordInput) passwordInput.value = '';
            if (congregacionInput) congregacionInput.value = '';
        } else {
            let mensajeError = data.detail || "Revise los datos introducidos.";
            if (errorDiv) {
                errorDiv.style.display = 'block';
                errorDiv.textContent = mensajeError;
            } else {
                alert("Error en el registro: " + mensajeError);
            }
        }
    } catch (err) {
        console.error("Error de red al registrar:", err);
        alert("Error de conexión con el servidor.");
    }
}

// VER / OCULTAR CONTRASEÑA
function alternarVisibilidadPassword() {
    const inputPass = document.getElementById('login-password');
    const iconoOjo = document.getElementById('iconoOjo');
    
    if (inputPass && iconoOjo) {
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
}

// CERRAR SESIÓN
function cerrarSesion() {
    localStorage.removeItem('sesion_activa');
    localStorage.removeItem('usuario');
    localStorage.removeItem('rol');
    localStorage.removeItem('congregacion');
    localStorage.removeItem('congregacion_id');
    location.reload();
}

// COMPROBAR SESIÓN AL CARGAR LA PÁGINA
document.addEventListener("DOMContentLoaded", () => {
    const sesionActiva = localStorage.getItem('sesion_activa');
    const rol = localStorage.getItem('rol');

    if (sesionActiva === 'true') {
        // Si ya hay sesión, ocultamos login/registro y mostramos la app
        cambiarVistaSesion(true, rol);
    } else {
        // Si no hay sesión, aseguramos que se vea el login
        cambiarVistaSesion(false);
    }
});

// Mostrar la pantalla de Login y ocultar la de Registro
function mostrarLogin() {
    const regScreen = document.getElementById('register-screen');
    const loginScreen = document.getElementById('login-screen');
    
    if (regScreen) {
        regScreen.classList.add('d-none');
        regScreen.style.display = 'none';
    }
    if (loginScreen) {
        loginScreen.classList.remove('d-none');
        loginScreen.style.display = 'flex';
    }
}

// Mostrar la pantalla de Registro y ocultar la de Login
function mostrarRegistro() {
    const loginScreen = document.getElementById('login-screen');
    const regScreen = document.getElementById('register-screen');
    
    if (loginScreen) {
        loginScreen.classList.add('d-none');
        loginScreen.style.display = 'none';
    }
    if (regScreen) {
        regScreen.classList.remove('d-none');
        regScreen.style.display = 'flex';
    }

    cargarCongregacionesRegistro();
}

// Controladores para alternar pantallas de forma segura
document.addEventListener("DOMContentLoaded", () => {
    const btnIrLogin = document.getElementById('btn-ir-login');
    const loginScreen = document.getElementById('login-screen');
    const registerScreen = document.getElementById('register-screen');

    if (btnIrLogin) {
        btnIrLogin.addEventListener('click', () => {
            if (registerScreen) registerScreen.style.display = 'none';
            if (loginScreen) loginScreen.style.display = 'flex';
        });
    }
});

async function cargarCongregacionesRegistro() {
    try {
        const response = await fetch('/api/congregaciones');
        const congregaciones = await response.json();

        const select = document.getElementById('reg-congregacion');
        if (!select) return;

        select.innerHTML = '<option value="">Selecciona tu congregación...</option>';

        congregaciones.forEach(cong => {
            const option = document.createElement('option');
            option.value = cong.id;
            option.textContent = cong.nombre;
            select.appendChild(option);
        });

    } catch (error) {
        console.error("Error al cargar las congregaciones:", error);
    }
}
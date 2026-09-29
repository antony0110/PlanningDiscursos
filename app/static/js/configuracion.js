document.addEventListener("DOMContentLoaded", () => {
    cargarConfiguracionCongregacion();

    const btnEditar = document.getElementById("btn-habilitar-edicion");
    const btnCancelar = document.getElementById("btn-cancelar-edicion");
    const formConfig = document.getElementById("form-config-congre");

    if (btnEditar) {
        btnEditar.addEventListener("click", () => alternarEdicion(true));
    }

    if (btnCancelar) {
        btnCancelar.addEventListener("click", () => {
            alternarEdicion(false);
            cargarConfiguracionCongregacion(); // Vuelve a cargar los datos originales
        });
    }

    if (formConfig) {
        formConfig.addEventListener("submit", guardarConfigCongregacion);
    }
});

function alternarEdicion(activar) {
    const inputs = document.querySelectorAll("#form-config-congre input");
    inputs.forEach(input => {
        input.disabled = !activar;
    });

    const btnEditar = document.getElementById("btn-habilitar-edicion");
    const contenedorBotones = document.getElementById("contenedor-botones");

    if (activar) {
        btnEditar.style.display = "none";
        contenedorBotones.style.setProperty("display", "flex", "important");
    } else {
        btnEditar.style.display = "block";
        contenedorBotones.style.setProperty("display", "none", "important");
    }
}

async function cargarConfiguracionCongregacion() {
    try {
        const response = await fetch("/api/congregacion/config", {
            method: "GET",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });

        if (response.ok) {
            const data = await response.json();
            
            // Eliminamos la línea del lbl-nombre-congregacion que ya no existe
            document.getElementById("cfg-nombre").value = data.nombre || "";
            document.getElementById("cfg-direccion").value = data.direccion || "";
            document.getElementById("cfg-hora").value = data.hora_reunion || "";
            document.getElementById("cfg-email").value = data.email_multimedia || "";
            document.getElementById("cfg-nombre-coordinador").value = data.nombre_coordinadordiscursospublicos || data.nombre_coordinador || "";
            document.getElementById("cfg-telefono").value = data.telefono_coordinador || "";
            
            alternarEdicion(false); // Bloquea por defecto al entrar
        }
    } catch (error) {
        console.error("Error al cargar configuración:", error);
    }
}

async function guardarConfigCongregacion(e) {
    e.preventDefault();

    const payload = {
        nombre: document.getElementById("cfg-nombre").value,
        direccion: document.getElementById("cfg-direccion").value,
        hora_reunion: document.getElementById("cfg-hora").value,
        email_multimedia: document.getElementById("cfg-email").value,
        nombre_coordinadordiscursospublicos: document.getElementById("cfg-nombre-coordinador").value,
        telefono_coordinador: document.getElementById("cfg-telefono").value
    };

    try {
        const response = await fetch("/api/congregacion/config", {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("¡Configuración actualizada con éxito!");
            alternarEdicion(false);
            cargarConfiguracionCongregacion();
        } else {
            alert("Error al actualizar la configuración.");
        }
    } catch (error) {
        console.error("Error en la petición PUT:", error);
    }
}
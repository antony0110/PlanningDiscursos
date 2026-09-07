window.cargarHistorico = async function() {
    console.log("¡EJECUTANDO HISTÓRICO ORDENADO DE MENOS A MÁS!");
    try {
        const response = await fetch('/api/historico');
        if (!response.ok) throw new Error("Error al obtener el histórico");
        
        const data = await response.json();
        const tabla = document.getElementById('tabla-historico');
        if (!tabla) return;

        const theadTr = tabla.querySelector('thead tr');
        const tbody = tabla.querySelector('tbody');
        if (!theadTr || !tbody) return;

        // 1. Recopilar dinámicamente todos los años únicos
        const aniosSet = new Set();
        data.forEach(d => {
            if (d.fechas_por_anio) {
                Object.keys(d.fechas_por_anio).forEach(anio => aniosSet.add(anio));
            }
        });
        
        // Ordenar los años de forma ascendente (más antiguos a la izquierda, ej: 2025, 2026...)
        const aniosOrdenados = Array.from(aniosSet).sort();

        // 2. Definir una paleta de colores de Bootstrap para rotar por año
        const paletaColores = [
            'bg-primary', 
            'bg-success', 
            'bg-danger', 
            'bg-warning text-dark', 
            'bg-info text-dark', 
            'bg-dark',
            'bg-secondary'
        ];

        // Asignar un color fijo a cada año según su posición
        const anioColorMap = {};
        aniosOrdenados.forEach((anio, index) => {
            anioColorMap[anio] = paletaColores[index % paletaColores.length];
        });

        // 3. Construir la cabecera
        let htmlCabecera = `
            <th style="width: 70px;">Nº</th>
            <th class="text-start">Tema del Discurso</th>
        `;
        aniosOrdenados.forEach(anio => {
            htmlCabecera += `<th style="width: 120px; text-align: center;">${anio}</th>`;
        });
        theadTr.innerHTML = htmlCabecera;

        // 4. Construir las filas usando el color correspondiente a cada año
        tbody.innerHTML = data.map(d => {
            let htmlFila = `
                <tr>
                    <td><strong>${d.numero || '-'}</strong></td>
                    <td class="text-start">${d.titulo || 'Sin título'}</td>
            `;

            aniosOrdenados.forEach(anio => {
                const fecha = d.fechas_por_anio && d.fechas_por_anio[anio];
                if (fecha) {
                    const claseColor = anioColorMap[anio];
                    htmlFila += `<td style="text-align: center;"><span class="badge ${claseColor}">${fecha}</span></td>`;
                } else {
                    htmlFila += `<td style="text-align: center;" class="text-muted">-</td>`;
                }
            });

            htmlFila += `</tr>`;
            return htmlFila;
        }).join('');

        console.log("¡Histórico ordenado cronológicamente de izquierda a derecha con éxito!");
    } catch (err) {
        console.error("Error en histórico:", err);
    }
};
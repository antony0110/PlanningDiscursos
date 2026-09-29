import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from datetime import datetime

def formatear_fecha_y_dia(fecha_str: str) -> tuple:
    """Convierte una fecha 'YYYY-MM-DD' en el día de la semana y texto legible."""
    try:
        dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        
        # Días de la semana en español (0: Lunes ... 6: Domingo)
        dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        dia_semana = dias_semana[dt.weekday()]
        
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        fecha_formateada = f"{dt.day} de {meses[dt.month - 1]} del {dt.year}"
        
        return dia_semana, fecha_formateada
    except Exception:
        # Por si hubiera algún fallo o viene ya en otro formato
        return "domingo", fecha_str

def generar_pdf_invitacion(output_path: str, datos: dict):
    # Crear el documento A4 con márgenes de 2 cm
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1A365D'),
        alignment=0
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748')
    )

    story = []

    # Extraer datos dinámicos de la congregación y del coordinador con valores por defecto
    congregacion_nombre = datos.get('congregacion_nombre', 'Nuestra Congregación')
    congregacion_direccion = datos.get('congregacion_direccion', '')
    email_multimedia = datos.get('congregacion_email_multimedia', 'correo@multimedia.com')
    
    # Cogemos el nombre del coordinador de discursos público configurado en la congregación
    usuario_nombre = (
        datos.get('nombre_coordinadordiscursospublicos') or 
        datos.get('nombre_coordinador') or 
        datos.get('usuario_nombre', 'Coordinador de discursos')
    )
    usuario_telefono = datos.get('usuario_telefono', '')
    usuario_email = datos.get('usuario_email', '')

    # 1. Cabecera - Datos Dinámicos de la Congregación
    story.append(Paragraph(f"<b>Congregación de {congregacion_nombre}</b>", title_style))
    if congregacion_direccion:
        story.append(Paragraph(congregacion_direccion, body_style))
    story.append(Spacer(1, 15))

    # 2. Saludo al Orador
    story.append(Paragraph(f"Querido hermano <b>{datos.get('orador_nombre', '')}</b>,", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>NOS GUSTARÍA INVITARTE A NUESTRA CONGREGACIÓN, PARA QUE PUDIERAS DISCURSAR.</b>", body_style))
    story.append(Spacer(1, 15))

    # 3. Bloque de Discurso y Fecha (Tabla destacada)
    fecha_cruda = datos.get('fecha_texto') or datos.get('fecha', '')
    dia_semana, fecha_formateada = formatear_fecha_y_dia(fecha_cruda)

    discurso_texto = f"<b>{datos.get('numero_discurso', '')}.-</b> {datos.get('titulo_discurso', '')}"
    fecha_texto = f"El discurso será el <b>{dia_semana}</b>, <b>{fecha_formateada}</b> a las <b>{datos.get('congregacion_hora_reunion', '11:00')}</b> en la dirección arriba indicada."

    tabla_datos = [
        [Paragraph("<b>Bosquejo y tema:</b>", body_style), Paragraph(discurso_texto, body_style)],
        [Paragraph("<b>Fecha y hora:</b>", body_style), Paragraph(fecha_texto, body_style)]
    ]

    t = Table(tabla_datos, colWidths=[110, 400])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EDF2F7')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # 4. Instrucciones Multimedia Dinámicas y Confirmación
    texto_multimedia = (
        f"En el caso de utilizar imágenes, por favor remítelas lo antes posible al siguiente correo electrónico: "
        f"<b>{email_multimedia}</b> e indícanos también el número de la canción que utilizarás."
    )
    story.append(Paragraph(texto_multimedia, body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Por otra parte, te ruego me confirmes si aceptas este privilegio a la mayor brevedad posible.<br/><br/>"
        "En el caso de que surgiera un imprevisto a pocos días de la fecha indicada y no pudieras atender esta invitación, "
        "ten la bondad de comunicármelo a la mayor brevedad posible. En tal caso te agradecería que en colaboración con el "
        "coordinador de discursos de tu congregación, nos recomendarais otro orador que pudiera sustituirte.",
        body_style
    ))
    story.append(Spacer(1, 20))

    # 5. Firma Dinámica del Coordinador y Teléfono/Email
    contacto_linea = f"{usuario_telefono} | {usuario_email}".strip(" |")
    firma_texto = f"<b>{usuario_nombre}</b><br/>Coordinador de discursos Congregación {congregacion_nombre}"
    if contacto_linea:
        firma_texto += f"<br/>{contacto_linea}"

    story.append(Paragraph("Muchas gracias por tu buena disposición y colaboración.<br/>Un abrazo,", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(firma_texto, body_style))

    # Construir el PDF
    doc.build(story)
    return output_path
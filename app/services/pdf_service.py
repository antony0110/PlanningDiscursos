import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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

    # 1. Cabecera - Datos de la Congregación
    story.append(Paragraph("<b>Congregación de Algemesí</b>", title_style))
    story.append(Paragraph("Carrer Germaníes, 56, bajo. L'Alcudia. (Valencia)", body_style))
    story.append(Spacer(1, 15))

    # 2. Saludo al Orador
    story.append(Paragraph(f"Querido hermano <b>{datos.get('orador_nombre', '')}</b>,", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>NOS GUSTARÍA INVITARTE A NUESTRA CONGREGACIÓN, PARA QUE PUDIERAS DISCURSAR.</b>", body_style))
    story.append(Spacer(1, 15))

    # 3. Bloque de Discurso y Fecha (Tabla destacada)
    discurso_texto = f"<b>{datos.get('numero_discurso', '')}.-</b> {datos.get('titulo_discurso', '')}"
    fecha_texto = f"El discurso será el domingo, <b>{datos.get('fecha_texto', '')}</b> a las <b>11:00 horas</b> en la dirección arriba indicada."

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

    # 4. Instrucciones Multimedia y Confirmación
    story.append(Paragraph(
        "En el caso de utilizar imágenes, por favor remítelas lo antes posible al siguiente correo electrónico: "
        "<b>algemesimultimedia@gmail.com</b> e indícanos también el número de la canción que utilizarás.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Por otra parte, te ruego me confirmes si aceptas este privilegio a la mayor brevedad posible.<br/><br/>"
        "En el caso de que surgiera un imprevisto a pocos días de la fecha indicada y no pudieras atender esta invitación, "
        "ten la bondad de comunicármelo a la mayor brevedad posible. En tal caso te agradecería que en colaboración con el "
        "coordinador de discursos de tu congregación, nos recomendarais otro orador que pudiera sustituirte.",
        body_style
    ))
    story.append(Spacer(1, 20))

    # 5. Firma del Coordinador
    story.append(Paragraph("Muchas gracias por tu buena disposición y colaboración.<br/>Un abrazo,", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Antony Gomez Carrasco</b><br/>Coordinador de discursos Congregación Algemesí<br/>651 174 827 | antonygomezcarrasco@gmail.com", body_style))

    # Construir el PDF
    doc.build(story)
    return output_path
import os
import re
import unicodedata
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.db import models

def limpiar_nombre_congregacion(nombre):
    if not nombre:
        return "Local"
    
    texto = str(nombre).strip()
    lower_val = texto.lower()
    
    if lower_val in ['', 'nan', 'nat', 'none', '-', '--', 'coordinador/a']:
        return "Local"
    if any(w in lower_val for w in ['coordinador', 'coordinadora', 'cargo']):
        return "Local"
        
    texto = texto.rstrip(':').strip()
    return texto.title()

def generar_clave_normalizada(nombre):
    if not nombre:
        return "local"
    t = str(nombre).lower()
    t = (t.replace('\u2013', '').replace('\u2014', '').replace('\u2011', '')
         .replace('-', '').replace("'", "").replace("´", "").replace("`", "").replace(" ", ""))
    nfkd = unicodedata.normalize('NFKD', t)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def importar_archivo(nombre_archivo, anio_objetivo):
    if not os.path.exists(nombre_archivo):
        print(f"❌ No se encuentra el archivo '{nombre_archivo}'")
        return

    print(f"📂 Importando '{nombre_archivo}' forzando el año {anio_objetivo}...")
    
    db: Session = SessionLocal()

    # Limpieza previa de planificaciones de ese año para evitar duplicar el calendario
    inicio_anio = datetime(anio_objetivo, 1, 1).date()
    fin_anio = datetime(anio_objetivo, 12, 31).date()
    db.query(models.Planificacion).filter(
        models.Planificacion.fecha >= inicio_anio,
        models.Planificacion.fecha <= fin_anio
    ).delete()
    db.commit()

    df_raw = pd.read_excel(nombre_archivo, header=None)
    header_idx = 0
    for i, row in df_raw.iterrows():
        if any('fecha' in str(val).lower() for val in row.values):
            header_idx = i
            break

    df = pd.read_excel(nombre_archivo, skiprows=header_idx)
    df.columns = df.columns.astype(str).str.strip()

    creados = 0

    for _, row in df.iterrows():
        val_fecha = None
        for col in df.columns:
            if 'fecha' in col.lower() and 'envio' not in col.lower():
                v = row.get(col)
                if pd.notna(v):
                    try:
                        f_Parsed = pd.to_datetime(v)
                        val_fecha = datetime(anio_objetivo, f_Parsed.month, f_Parsed.day).date()
                        break
                    except:
                        pass
        
        if not val_fecha:
            continue

        # Orador
        orador_nombre = "Por asignar"
        for col in df.columns:
            if 'orador' in col.lower():
                v = row.get(col)
                if pd.notna(v) and str(v).strip().lower() not in ['nan', 'nat', '', 'none', '-']:
                    orador_nombre = str(v).strip()
                break

        es_evento = False
        texto_evento = None
        palabras_clave = ['asamblea', 'visita', 'discurso especial', 'circuito', 'representante', 'conmemoración', 'regional']
        if any(kw in orador_nombre.lower() for kw in palabras_clave):
            es_evento = True
            texto_evento = orador_nombre
            orador_nombre = "Desconocido"

        # Congregación con normalización estricta para evitar duplicados
        cong_raw = "Propia"
        for col in df.columns:
            if 'congregac' in col.lower():
                v = row.get(col)
                if pd.notna(v) and str(v).strip().lower() not in ['nan', 'nat', 'none', '', '-']:
                    cong_raw = str(v).strip()
                break

        cong_nombre_limpio = limpiar_nombre_congregacion(cong_raw)
        clave_actual = generar_clave_normalizada(cong_nombre_limpio)

        congregacion_db = None
        todas_cong = db.query(models.Congregacion).all()
        for c in todas_cong:
            if generar_clave_normalizada(c.nombre) == clave_actual:
                congregacion_db = c
                break

        if not congregacion_db:
            congregacion_db = models.Congregacion(nombre=cong_nombre_limpio)
            db.add(congregacion_db)
            db.commit()
            db.refresh(congregacion_db)

        orador_db = None
        if orador_nombre not in ["Desconocido", "Por asignar"]:
            orador_db = db.query(models.Orador).filter(models.Orador.nombre.ilike(orador_nombre)).first()
            if not orador_db:
                orador_db = models.Orador(nombre=orador_nombre, telefono="", congregacion_id=congregacion_db.id)
                db.add(orador_db)
                db.commit()
                db.refresh(orador_db)

        # Bosquejo
        num_bosquejo = None
        titulo_bosquejo = ""
        for col in df.columns:
            if 'bosquejo' in col.lower() or 'tema' in col.lower():
                v = row.get(col)
                if pd.notna(v) and str(v).strip().lower() not in ['nan', 'nat', '-', '']:
                    tema_raw = str(v).strip()
                    match = re.match(r'^(\d+)[\.\-\s]+(.*)', tema_raw)
                    if match:
                        num_bosquejo = int(match.group(1))
                        titulo_bosquejo = match.group(2).strip()
                    elif tema_raw.isdigit():
                        num_bosquejo = int(tema_raw)
                    break

        # Invitación
        estado_inv = "No enviada"
        for col in df.columns:
            if 'invitaci' in col.lower():
                v = row.get(col)
                if pd.notna(v) and any(x in str(v).lower() for x in ['si', 'enviad', 'envia', 'enviado']):
                    estado_inv = "Enviada"
                break

        nueva_plan = models.Planificacion(
            fecha=val_fecha,
            id_orador=orador_db.id if orador_db else None,
            numero_bosquejo=num_bosquejo,
            estado_invitacion=estado_inv,
            estado_confirmacion="Confirmado",
            es_evento_especial=es_evento,
            texto_evento=texto_evento
        )
        db.add(nueva_plan)
        creados += 1

    db.commit()
    db.close()
    print(f"✅ ¡Importados {creados} registros para el año {anio_objetivo} con éxito!")

if __name__ == "__main__":
    importar_archivo("PlanAnual2025_Limpio.xlsx", 2025)
    importar_archivo("Planificacion_Procesada.xlsx", 2026)
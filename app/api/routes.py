import os
import pandas as pd
import unicodedata

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from datetime import date, timedelta
from collections import defaultdict
from pydantic import BaseModel
from app.db.database import get_db
from app.db import models, schemas
from app.services.pdf_service import generar_pdf_invitacion
from app.db.models import Bosquejo
from app.db.models import Congregacion  # Asegúrate de importar tu modelo Congregacion
import bcrypt

router = APIRouter()


# --- FUNCIÓN DE DEPENDENCIAS (Definida arriba para que esté disponible) ---
def get_current_user(x_username: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Obtiene el usuario actual basándose estrictamente en la cabecera X-Username"""
    if not x_username:
        raise HTTPException(status_code=401, detail="Falta la cabecera de autenticación del usuario")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.username == x_username).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en el sistema")
        
    return usuario
# --------------------------------------------------------------------------


@router.get("/congregaciones", response_model=List[schemas.CongregacionOut])
def listar_congregaciones(db: Session = Depends(get_db)):
    return db.query(models.Congregacion).all()


@router.get("/oradores", response_model=List[schemas.OradorOut])
def listar_oradores(
    congregacion_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)  # Inyectamos el usuario logueado
):
    query = db.query(models.Orador).options(selectinload(models.Orador.discursos))
    
    # Comprobamos si el parámetro ha sido enviado explícitamente en la petición
    if congregacion_id is not None:
        if congregacion_id != 0:  # Si es un ID válido distinto de 0, filtramos por esa congregación
            query = query.filter(models.Orador.congregacion_id == congregacion_id)
        # Si congregacion_id == 0 (que es lo que manda "Todas las congregaciones"), 
        # no aplicamos ningún filtro, devolviendo todas. 
    return query.all()


@router.get("/oradores/buscar-por-discurso", response_model=List[schemas.OradorOut])
def buscar_por_discurso(numero: int, db: Session = Depends(get_db)):
    oradores = (
        db.query(models.Orador)
        .join(models.DiscursoOrador)
        .filter(models.DiscursoOrador.numero_discurso == numero)
        .all()
    )
    return oradores


class OradorCreateSchema(BaseModel):
    nombre: str
    telefono: Optional[str] = ""
    congregacion_id: Optional[int] = None
    discursos: List[int] = []


@router.post("/oradores")
def crear_orador_manual(datos: OradorCreateSchema, db: Session = Depends(get_db)):
    """Crea un nuevo orador manualmente con su congregación y discursos"""
    existe = db.query(models.Orador).filter(models.Orador.nombre.ilike(datos.nombre.strip())).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un orador registrado con ese nombre.")
    
    nuevo_orador = models.Orador(
        nombre=datos.nombre.strip(),
        telefono=datos.telefono.strip() if datos.telefono else None,
        congregacion_id=datos.congregacion_id
    )
    db.add(nuevo_orador)
    db.commit()
    db.refresh(nuevo_orador)

    for num_disc in datos.discursos:
        db.add(models.DiscursoOrador(orador_id=nuevo_orador.id, numero_discurso=num_disc))
    
    db.commit()
    return {"status": "success", "mensaje": "Orador creado correctamente"}


@router.get("/invitacion/pdf")
def descargar_invitacion_pdf(
    orador_nombre: str,
    numero_discurso: str,
    titulo_discurso: str,
    fecha_texto: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    os.makedirs("data/temp", exist_ok=True)
    pdf_path = "data/temp/invitacion_temp.pdf"
    
    # Buscamos la congregación utilizando el ID del usuario de manera explícita
    cong = None
    if hasattr(current_user, 'congregacion_id') and current_user.congregacion_id:
        cong = db.query(Congregacion).filter(Congregacion.id == current_user.congregacion_id).first()
    
    datos = {
        "orador_nombre": orador_nombre,
        "numero_discurso": numero_discurso,
        "titulo_discurso": titulo_discurso,
        "fecha_texto": fecha_texto,
        
        "congregacion_nombre": cong.nombre if cong else "",
        "congregacion_direccion": getattr(cong, 'direccion', '') or "",
        "congregacion_email_multimedia": getattr(cong, 'email_multimedia', '') or "",
        "congregacion_hora_reunion": getattr(cong, 'hora_reunion', '') or "11:00",
        # Tomamos el nombre del coordinador guardado en los ajustes de congregación, o el username por defecto
        "usuario_nombre": getattr(cong, 'nombre_coordinadordiscursospublicos', '') or current_user.username,
        "usuario_telefono": getattr(cong, 'telefono_coordinador', '') or "",
        "usuario_email": getattr(current_user, 'email', '') or ""
    }
    
    generar_pdf_invitacion(pdf_path, datos)
    
    return FileResponse(
        pdf_path, 
        filename=f"Invitacion_{orador_nombre.replace(' ', '_')}.pdf",
        media_type="application/pdf"
    )

@router.get("/bosquejos/{numero}")
def obtener_bosquejo(numero: str, db: Session = Depends(get_db)):
    num_limpio = ''.join(filter(str.isdigit, str(numero)))
    
    if not num_limpio:
        return {"numero": 0, "titulo": ""}
        
    num_int = int(num_limpio)
    bosquejo = db.query(Bosquejo).filter(Bosquejo.numero == num_int).first()
    
    if not bosquejo:
        return {"numero": num_int, "titulo": f"Tema del Discurso Nº {num_int} (Sin registrar en BD)"}
        
    return {"numero": bosquejo.numero, "titulo": bosquejo.titulo}


@router.get("/planificacion", response_model=List[schemas.PlanificacionResponse])
def obtener_planificacion(
    anio: Optional[int] = None, 
    congregacion_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    # Determinamos qué congregación vamos a consultar/gestionar
    target_congregacion_id = congregacion_id if congregacion_id else usuario_actual.congregacion_id
    
    # Año objetivo (si no se pasa, usamos el actual, por ejemplo 2026)
    target_anio = anio if anio else date.today().year

    # 1. Comprobamos si existen planificaciones para esta congregación en este año
    existe_planificacion = db.query(models.Planificacion).filter(
        models.Planificacion.congregacion_id == target_congregacion_id,
        models.Planificacion.fecha >= date(target_anio, 1, 1),
        models.Planificacion.fecha <= date(target_anio, 12, 31)
    ).first() # <--- Aquí cerramos bien el paréntesis y el .first()

    # 2. Si NO tiene ninguna planificación, ejecutamos la función que autogenera el calendario
    if not existe_planificacion:
        # ⚠️ (Aquí llamas a tu función de autogenerado si la tienes creada, o déjalo con pass de momento)
        pass

    # 3. Construimos la consulta habitual para devolver los datos a la tabla
    query = db.query(
        models.Planificacion.id,
        models.Planificacion.fecha,
        models.Planificacion.id_orador,
        models.Orador.nombre.label("orador_nombre"),
        models.Orador.telefono.label("orador_telefono"),
        models.Congregacion.nombre.label("orador_congregacion"),
        models.Planificacion.numero_bosquejo,
        models.Bosquejo.titulo.label("bosquejo_tema"),
        models.Planificacion.estado_invitacion,
        models.Planificacion.estado_confirmacion,
        models.Planificacion.fecha_envio.label("fecha_envio_invitacion"),
        models.Planificacion.es_evento_especial,
        models.Planificacion.texto_evento
    ).outerjoin(models.Orador, models.Planificacion.id_orador == models.Orador.id)\
     .outerjoin(models.Congregacion, models.Orador.congregacion_id == models.Congregacion.id)\
     .outerjoin(models.Bosquejo, models.Planificacion.numero_bosquejo == models.Bosquejo.numero)

    # Filtramos por la congregación correspondiente
    query = query.filter(models.Planificacion.congregacion_id == target_congregacion_id)

    if anio:
        query = query.filter(
            models.Planificacion.fecha >= date(anio, 1, 1),
            models.Planificacion.fecha <= date(anio, 12, 31)
        )

    return query.order_by(models.Planificacion.fecha.asc()).all()

@router.post("/planificacion/generar-anio/{anio}")
def generar_planificacion_anio(
    anio: int, 
    dia_reunion: int = 6, # 5 para Sábado, 6 para Domingo (por defecto domingo)
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    existentes = db.query(models.Planificacion).filter(
        models.Planificacion.congregacion_id == usuario_actual.congregacion_id,
        models.Planificacion.fecha >= date(anio, 1, 1),
        models.Planificacion.fecha <= date(anio, 12, 31)
    ).first()

    if existentes:
        return {"message": f"El año {anio} ya existía para tu congregación."}

    fecha_actual = date(anio, 1, 1)
    
    # Buscamos el primer día de reunión que nos haya indicado el usuario
    while fecha_actual.weekday() != dia_reunion:
        fecha_actual += timedelta(days=1)

    nuevas_fechas = []
    while fecha_actual.year == anio:
        nuevas_fechas.append(
            models.Planificacion(
                fecha=fecha_actual,
                estado_invitacion="No enviada",
                estado_confirmacion="Pendiente",
                congregacion_id=usuario_actual.congregacion_id
            )
        )
        fecha_actual += timedelta(days=7) # Salto semanal exacto

    db.add_all(nuevas_fechas)
    db.commit()
    return {"message": f"Año {anio} generado correctamente."}


@router.patch("/planificacion/{id}")
def actualizar_planificacion(
    id: int, 
    datos: schemas.PlanificacionUpdate, 
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    # Opcional pero recomendado: Asegurar que la planificación pertenece a su congregación
    item = db.query(models.Planificacion).filter(
        models.Planificacion.id == id,
        models.Planificacion.congregacion_id == usuario_actual.congregacion_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Fecha no encontrada o sin permisos")
    
    for key, value in datos.dict(exclude_unset=True).items():
        setattr(item, key, value)
        
    db.commit()
    db.refresh(item)
    return item


@router.put("/planificacion/{fecha_id}")
def actualizar_planificacion_manual(
    fecha_id: int, 
    datos: schemas.PlanificacionUpdate, 
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    """Actualiza, asigna o vacía manualmente un orador y su bosquejo en una fecha concreta"""
    plan_item = db.query(models.Planificacion).filter(
        models.Planificacion.id == fecha_id,
        models.Planificacion.congregacion_id == usuario_actual.congregacion_id
    ).first()
    
    if not plan_item:
        raise HTTPException(status_code=404, detail="No se encuentra esa fecha o no pertenece a tu congregación.")
    
    datos_dict = datos.dict(exclude_unset=True)
    for key, value in datos_dict.items():
        setattr(plan_item, key, value)
    
    db.commit()
    db.refresh(plan_item)
    
    return {
        "status": "success",
        "mensaje": "Planificación actualizada correctamente"
    }

@router.delete("/{orador_id}")
def eliminar_orador(orador_id: int, forzar: bool = False, db: Session = Depends(get_db)):
    orador = db.query(models.Orador).filter(models.Orador.id == orador_id).first()
    
    if not orador:
        raise HTTPException(status_code=404, detail="Discursante no encontrado")

    if not forzar and orador.planificaciones:
        raise HTTPException(
            status_code=409, 
            detail="Este orador tiene fechas asignadas en el planificador. ¿Estás seguro de que quieres borrarlo y eliminar todas sus asignaciones?"
        )
    
    congregacion_id = orador.congregacion_id

    db.delete(orador)
    db.commit()
    
    if congregacion_id:
        oradores_restantes = db.query(models.Orador).filter(models.Orador.congregacion_id == congregacion_id).count()
        if oradores_restantes == 0:
            congregacion_a_borrar = db.query(models.Congregacion).filter(models.Congregacion.id == congregacion_id).first()
            if congregacion_a_borrar:
                db.delete(congregacion_a_borrar)
                db.commit()

    return {"mensaje": "Orador y congregación vacía eliminados correctamente"}


@router.get("/api/oradores/{orador_id}/discursos")
def obtener_discursos_orador(orador_id: int, db: Session = Depends(get_db)):
    orador = db.query(models.Orador).filter(models.Orador.id == orador_id).first()
    
    if not orador:
        return {"status": "error", "detalle": "Orador no encontrado"}
        
    return {
        "telefono": orador.telefono,
        "congregacion": orador.congregacion,
        "bosquejos": [{"numero": b.numero, "titulo": b.titulo} for b in orador.bosquejos]
    }


def limpiar_nombre_congregacion(nombre):
    if not nombre:
        return "Local"
    
    nombre_limpio = str(nombre).replace('\u2013', '-').replace('\u2014', '-').replace('\u2011', '-')
    nfkd = unicodedata.normalize('NFKD', nombre_limpio)
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    limpio = sin_tildes.strip().title()
    
    lower_val = limpio.lower()
    
    if lower_val in ['', 'nan', 'nat', 'none', '-', '--']:
        return "Local"
        
    if any(w in lower_val for w in ['coordinador', 'coordinadora', 'cargo']):
        return "Local"
        
    return limpio.rstrip(':').strip()


@router.get("/sincronizar-db-desde-excel")
def sincronizar_db_desde_excel(db: Session = Depends(get_db)):
    db.query(models.DiscursoOrador).delete()
    db.query(models.Orador).delete()
    db.query(models.Congregacion).delete()
    db.commit()

    archivos = ["Coordinadores_limpio.xlsx"]
    total_oradores = 0
    total_discursos = 0

    try:
        for archivo in archivos:
            df = pd.read_excel(archivo)
            df.columns = df.columns.astype(str).str.strip()
            
            col_cong = next((c for c in df.columns if 'congregac' in c.lower()), None)
            col_nombre = next((c for c in df.columns if 'nombre' in c.lower()), None)
            col_cargo = next((c for c in df.columns if c.lower() == 'cargo'), None)
            col_tel = next((c for c in df.columns if 'telefono' in c.lower() or 'teléfono' in c.lower()), None)
            col_disc = next((c for c in df.columns if c.lower() == 'discursos'), None)
            
            if not col_nombre:
                continue
                
            for _, row in df.iterrows():
                nombre = str(row.get(col_nombre, '')).strip()
                if not nombre or nombre.lower() in ['nan', 'nat', 'none', '']:
                    continue
                
                cong_raw = row.get(col_cong, 'Local') if col_cong else 'Local'
                cong_nombre = limpiar_nombre_congregacion(cong_raw)
                    
                congregacion = None
                todas_cong = db.query(models.Congregacion).all()
                for c in todas_cong:
                    if limpiar_nombre_congregacion(c.nombre) == cong_nombre:
                        congregacion = c
                        break
                
                if not congregacion:
                    congregacion = models.Congregacion(nombre=cong_nombre)
                    db.add(congregacion)
                    db.commit()
                    db.refresh(congregacion)
                
                cargo_val = str(row.get(col_cargo, '')).strip() if col_cargo else ''
                cargo_final = cargo_val if cargo_val and cargo_val.lower() != 'nan' and cargo_val != '-' else None
                
                tel_val = str(row.get(col_tel, '')).strip() if col_tel else ''
                tel_final = tel_val if tel_val and tel_val.lower() != 'nan' else None

                orador = db.query(models.Orador).filter(models.Orador.nombre.ilike(nombre)).first()
                if not orador and tel_final:
                    orador = db.query(models.Orador).filter(models.Orador.telefono == tel_final).first()
                
                if orador:
                    orador.congregacion_id = congregacion.id
                    if cargo_final:
                        orador.cargo = cargo_final
                    if tel_final:
                        orador.telefono = tel_final
                else:
                    orador = models.Orador(
                        nombre=nombre,
                        cargo=cargo_final,
                        telefono=tel_final,
                        congregacion_id=congregacion.id
                    )
                    db.add(orador)
                    db.commit()
                    db.refresh(orador)
                    total_oradores += 1

                if col_disc and not pd.isna(row.get(col_disc)):
                    discursos_val = row.get(col_disc)
                    partes = str(discursos_val).replace(';', ',').split(',')
                    for p in partes:
                        p_clean = ''.join(filter(str.isdigit, p))
                        if p_clean.isdigit():
                            num = int(p_clean)
                            existe = db.query(models.DiscursoOrador).filter_by(
                                orador_id=orador.id, 
                                numero_discurso=num
                            ).first()
                            if not existe:
                                db.add(models.DiscursoOrador(orador_id=orador.id, numero_discurso=num))
                                total_discursos += 1
            db.commit()
            
        return {
            "status": "success",
            "mensaje": "Base de datos sincronizada unificando congregaciones correctamente",
            "oradores_procesados": total_oradores,
            "discursos_asociados": total_discursos
        }
    except Exception as e:
        return {"status": "error", "detalle": str(e)}


@router.get("/sincronizar-bosquejos")
def sincronizar_bosquejos_desde_excel(db: Session = Depends(get_db)):
    archivo_bosquejos = "Titulos_discursos_publicos.xlsx"
    
    if not os.path.exists(archivo_bosquejos):
        return {
            "status": "error", 
            "detalle": f"No se encuentra el archivo '{archivo_bosquejos}' en la carpeta del proyecto."
        }

    try:
        df_bosquejos = pd.read_excel(archivo_bosquejos)
        df_bosquejos.columns = df_bosquejos.columns.astype(str).str.strip().str.lower()
        df_bosquejos.columns = df_bosquejos.columns.str.replace('.', '', regex=False).str.replace('º', '', regex=False)
        
        col_num = next((c for c in df_bosquejos.columns if 'n' in c or 'num' in c), df_bosquejos.columns[0])
        col_tit = next((c for c in df_bosquejos.columns if 'tit' in c or 'discurs' in c), df_bosquejos.columns[1])
            
        actualizados = 0
        creados = 0
        
        for _, row in df_bosquejos.iterrows():
            num_val = row.get(col_num)
            tit_val = row.get(col_tit)
            
            if pd.notna(num_val) and pd.notna(tit_val):
                num_limpio = ''.join(filter(str.isdigit, str(num_val)))
                if num_limpio.isdigit():
                    num_int = int(num_limpio)
                    titulo_str = str(tit_val).strip()
                    
                    bosquejo_db = db.query(models.Bosquejo).filter(models.Bosquejo.numero == num_int).first()
                    if bosquejo_db:
                        bosquejo_db.titulo = titulo_str
                        actualizados += 1
                    else:
                        db.add(models.Bosquejo(numero=num_int, titulo=titulo_str))
                        creados += 1
                        
        db.commit()
        
        return {
            "status": "success",
            "mensaje": "¡Bosquejos sincronizados correctamente!",
            "creados": creados,
            "actualizados": actualizados
        }
    except Exception as e:
        return {"status": "error", "detalle": str(e)}


class OradorUpdateSchema(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    congregacion_id: Optional[int] = None
    discursos: Optional[List[int]] = None


@router.put("/oradores/{orador_id}")
def actualizar_orador(orador_id: int, datos: OradorUpdateSchema, db: Session = Depends(get_db)):
    orador = db.query(models.Orador).filter(models.Orador.id == orador_id).first()
    
    if not orador:
        raise HTTPException(status_code=404, detail="Orador no encontrado")
    
    if datos.nombre is not None:
        orador.nombre = datos.nombre.strip()
    if datos.telefono is not None:
        orador.telefono = datos.telefono.strip() if datos.telefono else None
    if datos.congregacion_id is not None:
        orador.congregacion_id = datos.congregacion_id
        
    if datos.discursos is not None:
        db.query(models.DiscursoOrador).filter(models.DiscursoOrador.orador_id == orador_id).delete()
        for num_disc in datos.discursos:
            db.add(models.DiscursoOrador(orador_id=orador_id, numero_discurso=num_disc))
            
    db.commit()
    db.refresh(orador)
    
    return {"status": "success", "mensaje": "Orador actualizado correctamente"}


class CongregacionCreateSchema(BaseModel):
    nombre: str


@router.post("/congregaciones", response_model=schemas.CongregacionOut)
def crear_congregacion(datos: CongregacionCreateSchema, db: Session = Depends(get_db)):
    nombre_limpio = datos.nombre.strip()
    
    existe = db.query(models.Congregacion).filter(models.Congregacion.nombre.ilike(nombre_limpio)).first()
    if existe:
        return existe
        
    nueva = models.Congregacion(nombre=nombre_limpio)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/historico")
def obtener_historico_discursos(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # 🛡️ Filtramos estrictamente por la congregación del usuario logueado
    planificaciones = db.query(models.Planificacion).filter(
        models.Planificacion.congregacion_id == current_user.congregacion_id,
        models.Planificacion.numero_bosquejo.isnot(None)
    ).all()
    
    historico_dict = defaultdict(dict)
    
    for p in planificaciones:
        if p.fecha and p.numero_bosquejo:
            anio = p.fecha.year
            fecha_formateada = p.fecha.strftime("%d/%m/%Y")
            historico_dict[p.numero_bosquejo][anio] = fecha_formateada

    bosquejos = db.query(models.Bosquejo).all()
    resultado = []
    
    for b in bosquejos:
        resultado.append({
            "numero": b.numero,
            "titulo": b.titulo,
            "fechas_por_anio": historico_dict.get(b.numero, {})
        })
        
    return resultado


@router.get("/historico/bosquejo/{numero_bosquejo}")
def verificar_ultima_fecha_bosquejo(numero_bosquejo: int, db: Session = Depends(get_db)):
    """Comprueba cuándo fue la última vez que se impartió un bosquejo y si está programado a futuro"""
    hoy = date.today()
    limite_un_anio = hoy - timedelta(days=365)
    
    ultima_asignacion = (
        db.query(models.Planificacion)
        .filter(
            models.Planificacion.numero_bosquejo == numero_bosquejo,
            models.Planificacion.fecha >= limite_un_anio,
            models.Planificacion.fecha <= hoy
        )
        .order_by(models.Planificacion.fecha.desc())
        .first()
    )
    
    if ultima_asignacion:
        return {
            "encontrado_reciente": True,
            "ultima_fecha": ultima_asignacion.fecha.strftime("%Y-%m-%d"),
            "asignado_futuro": False,
            "fecha_futura": None
        }
    
    registro_futuro = (
        db.query(models.Planificacion)
        .filter(
            models.Planificacion.numero_bosquejo == numero_bosquejo,
            models.Planificacion.fecha > hoy
        )
        .order_by(models.Planificacion.fecha.asc())
        .first()
    )
    
    if registro_futuro:
        return {
            "encontrado_reciente": False,
            "ultima_fecha": None,
            "asignado_futuro": True,
            "fecha_futura": registro_futuro.fecha.strftime("%Y-%m-%d")
        }
    
    return {
        "encontrado_reciente": False,
        "ultima_fecha": None,
        "asignado_futuro": False,
        "fecha_futura": None
    }


@router.get("/historico/orador")
def verificar_historico_orador(nombre: str, db: Session = Depends(get_db)):
    hoy = date.today()
    
    ultima_vez = db.query(models.Planificacion).join(
        models.Orador, models.Planificacion.id_orador == models.Orador.id
    ).filter(
        models.Orador.nombre == nombre,
        models.Planificacion.fecha <= hoy
    ).order_by(models.Planificacion.fecha.desc()).first()
    
    if not ultima_vez:
        return {"encontrado_en_rango": False, "ultima_fecha": None}
        
    diferencia_dias = (hoy - ultima_vez.fecha).days
    
    if diferencia_dias <= 730:
        return {
            "encontrado_en_rango": True,
            "ultima_fecha": str(ultima_vez.fecha)
        }
    else:
        return {
            "encontrado_en_rango": False,
            "ultima_fecha": str(ultima_vez.fecha)
        }

@router.post("/auth/login")
def login(datos: schemas.LoginSchema, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    
    if not usuario or not verify_password(datos.password, usuario.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
        
    # Obtenemos el nombre de la congregación gracias a la relación que tienes en models.py
    nombre_congregacion = usuario.congregacion_rel.nombre if usuario.congregacion_rel else "Sin congregación"

    return {
        "status": "success",
        "username": usuario.username,
        "rol": usuario.rol,
        "congregacion": nombre_congregacion, # <--- ¡Nuevo campo!
        "mensaje": "Login exitoso"
    }


@router.post("/crear-usuario")
def crear_usuario(datos: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # 1. Verificamos si se indicó que se quiere crear una nueva congregación por texto
    congregacion_id_final = datos.congregacion_id

    if hasattr(datos, 'nueva_congregacion_nombre') and datos.nueva_congregacion_nombre:
        nombre_nuevo = datos.nueva_congregacion_nombre.strip()
        if nombre_nuevo:
            # Creamos la congregación en la base de datos
            nueva_cong = models.Congregacion(
                nombre=nombre_nuevo,
                hora_reunion="11:00",
                nombre_coordinadordiscursospublicos=datos.username
            )
            db.add(nueva_cong)
            db.commit()
            db.refresh(nueva_cong)
            
            # Asignamos el ID generado a la variable final
            congregacion_id_final = nueva_cong.id

    # 2. Comprobamos si el usuario ya existe
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso.")

    # 3. Hasheamos la contraseña y creamos el usuario asociado a la congregación final
    hashed_password = bcrypt.hashpw(datos.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    nuevo_usuario = models.Usuario(
        username=datos.username,
        hashed_password=hashed_password,
        rol=datos.rol or "admin",
        congregacion_id=congregacion_id_final
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"mensaje": "Usuario y congregación creados con éxito", "id": nuevo_usuario.id}

def hash_password(password: str) -> str:
    """Hashea una contraseña utilizando bcrypt nativo."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra el hash guardado."""
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


class CongregacionConfigUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    hora_reunion: Optional[str] = None
    email_multimedia: Optional[str] = None
    telefono_coordinador: Optional[str] = None
    nombre_coordinadordiscursospublicos: Optional[str] = None  # 📌 Debe coincidir con el modelo de la BD

@router.get("/congregacion/config")
def obtener_config_congregacion(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Buscamos directamente por el ID que tiene el usuario vinculado
    congregacion = None
    if current_user.congregacion_id:
        congregacion = db.query(models.Congregacion).filter(models.Congregacion.id == current_user.congregacion_id).first()

    if not congregacion:
        return {
            "nombre": "",
            "direccion": "",
            "hora_reunion": "",
            "email_multimedia": "",
            "telefono_coordinador": "",
            "nombre_coordinadordiscursospublicos": ""
        }
    
    return {
        "nombre": congregacion.nombre or "",
        "direccion": congregacion.direccion or "",
        "hora_reunion": getattr(congregacion, 'hora_reunion', '') or "",
        "email_multimedia": congregacion.email_multimedia or "",
        "telefono_coordinador": congregacion.telefono_coordinador or "",
        "nombre_coordinadordiscursospublicos": getattr(congregacion, 'nombre_coordinadordiscursospublicos', '') or ""
    }

@router.put("/congregacion/config")
def actualizar_config_congregacion(
    config: CongregacionConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # 1. Si el usuario aún no tiene ninguna congregación vinculada, la creamos ahora mismo
    if not current_user.congregacion_id:
        nueva_congregacion = models.Congregacion()
        db.add(nueva_congregacion)
        db.commit()
        db.refresh(nueva_congregacion)
        
        # Vinculamos la nueva congregación al usuario y guardamos en la tabla de usuarios
        current_user.congregacion_id = nueva_congregacion.id
        db.commit()

    # 2. Buscamos la congregación usando el ID del usuario
    congregacion = db.query(models.Congregacion).filter(models.Congregacion.id == current_user.congregacion_id).first()
    if not congregacion:
        raise HTTPException(status_code=404, detail="Congregación no encontrada")

    # 3. Actualizamos los campos
    if config.nombre is not None:
        congregacion.nombre = config.nombre
    if config.direccion is not None:
        congregacion.direccion = config.direccion
    if config.hora_reunion is not None:
        congregacion.hora_reunion = config.hora_reunion
    if config.email_multimedia is not None:
        congregacion.email_multimedia = config.email_multimedia
    if config.telefono_coordinador is not None:
        congregacion.telefono_coordinador = config.telefono_coordinador
    if config.nombre_coordinadordiscursospublicos is not None:
        congregacion.nombre_coordinadordiscursospublicos = config.nombre_coordinadordiscursospublicos

    db.commit()
    return {"message": "Configuración guardada correctamente"}
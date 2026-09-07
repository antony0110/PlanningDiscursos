import os
import pandas as pd
import unicodedata

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from datetime import date, timedelta
from collections import defaultdict
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.db import models, schemas
from app.services.pdf_service import generar_pdf_invitacion
from app.db.models import Bosquejo
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext

router = APIRouter()


@router.get("/congregaciones", response_model=List[schemas.CongregacionOut])
def listar_congregaciones(db: Session = Depends(get_db)):
    return db.query(models.Congregacion).all()


@router.get("/oradores", response_model=List[schemas.OradorOut])
def listar_oradores(
    congregacion_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Orador).options(selectinload(models.Orador.discursos))
    if congregacion_id:
        query = query.filter(models.Orador.congregacion_id == congregacion_id)
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
    
    # Verificar si ya existe un orador con el mismo nombre
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

    

    # Asociar los discursos
    for num_disc in datos.discursos:
        db.add(models.DiscursoOrador(orador_id=nuevo_orador.id, numero_discurso=num_disc))
    
    db.commit()
    
    return {"status": "success", "mensaje": "Orador creado correctamente"}


@router.get("/invitacion/pdf")
def descargar_invitacion_pdf(
    orador_nombre: str,
    numero_discurso: str,
    titulo_discurso: str,
    fecha_texto: str
):
    os.makedirs("data/temp", exist_ok=True)
    pdf_path = "data/temp/invitacion_temp.pdf"
    
    datos = {
        "orador_nombre": orador_nombre,
        "numero_discurso": numero_discurso,
        "titulo_discurso": titulo_discurso,
        "fecha_texto": fecha_texto
    }
    
    generar_pdf_invitacion(pdf_path, datos)
    
    return FileResponse(
        pdf_path, 
        filename=f"Invitacion_{orador_nombre.replace(' ', '_')}.pdf",
        media_type="application/pdf"
    )


@router.get("/bosquejos/{numero}")
def obtener_bosquejo(numero: str, db: Session = Depends(get_db)):
    # Extraer únicamente los dígitos por si el frontend envía texto o formato especial
    num_limpio = ''.join(filter(str.isdigit, str(numero)))
    
    if not num_limpio:
        return {"numero": 0, "titulo": ""}
        
    num_int = int(num_limpio)
    bosquejo = db.query(Bosquejo).filter(Bosquejo.numero == num_int).first()
    
    if not bosquejo:
        # Fallback descriptivo para que no se quede vacío
        return {"numero": num_int, "titulo": f"Tema del Discurso Nº {num_int} (Sin registrar en BD)"}
        
    return {"numero": bosquejo.numero, "titulo": bosquejo.titulo}


@router.get("/planificacion", response_model=List[schemas.PlanificacionResponse])
def obtener_planificacion(anio: Optional[int] = None, db: Session = Depends(get_db)):
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

    if anio:
        query = query.filter(
            models.Planificacion.fecha >= date(anio, 1, 1),
            models.Planificacion.fecha <= date(anio, 12, 31)
        )

    return query.order_by(models.Planificacion.fecha.asc()).all()


@router.post("/planificacion/generar-anio/{anio}")
def generar_planificacion_anio(anio: int, db: Session = Depends(get_db)):
    existentes = db.query(models.Planificacion).filter(
        models.Planificacion.fecha >= date(anio, 1, 1),
        models.Planificacion.fecha <= date(anio, 12, 31)
    ).first()

    if existentes:
        return {"message": f"El año {anio} ya existía."}

    fecha_actual = date(anio, 1, 1)
    while fecha_actual.weekday() != 6:
        fecha_actual += timedelta(days=1)

    nuevas_fechas = []
    while fecha_actual.year == anio:
        nuevas_fechas.append(
            models.Planificacion(
                fecha=fecha_actual,
                estado_invitacion="No enviada",
                estado_confirmacion="Pendiente"
            )
        )
        fecha_actual += timedelta(days=7)

    db.add_all(nuevas_fechas)
    db.commit()
    return {"message": f"Año {anio} generado."}


@router.patch("/planificacion/{id}")
def actualizar_planificacion(id: int, datos: schemas.PlanificacionUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Planificacion).filter(models.Planificacion.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Fecha no encontrada")
    
    for key, value in datos.dict(exclude_unset=True).items():
        setattr(item, key, value)
        
    db.commit()
    db.refresh(item)
    return item

#Actualizar Planificación con datos manuales
class ActualizarAsignacionSchema(BaseModel):
    orador_id: Optional[int] = None
    nombre_orador: str
    telefono: Optional[str] = ""
    congregacion: str
    bosquejo_numero: int
    bosquejo_titulo: str

@router.put("/planificacion/{fecha_id}")
def actualizar_planificacion_manual(fecha_id: int, datos: schemas.PlanificacionUpdate, db: Session = Depends(get_db)):
    """Actualiza, asigna o vacía manualmente un orador y su bosquejo en una fecha concreta"""
    
    plan_item = db.query(models.Planificacion).filter(models.Planificacion.id == fecha_id).first()
    
    if not plan_item:
        raise HTTPException(status_code=404, detail="No se encuentra esa fecha en la planificación.")
    
    # Actualizamos solo los campos que vengan en la petición (permite enviar null para borrar)
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
            detail="Este orador tiene fechas asignadas en el planificador. ¿Estás seguro de que quieres borrarlo y eliminar todas suasignaciones?"
        )
    
    # 1. Guardamos el ID de la congregación antes de borrar al orador
    congregacion_id = orador.congregacion_id

    # 2. Borramos al orador
    db.delete(orador)
    db.commit()
    
    # 3. COMPROBACIÓN: Si tenía congregación, miramos si queda alguien más en ella
    if congregacion_id:
        oradores_restantes = db.query(models.Orador).filter(models.Orador.congregacion_id == congregacion_id).count()
        if oradores_restantes == 0:
            # Si no queda nadie, borramos también la congregación para que desaparezca de la lista
            congregacion_a_borrar = db.query(models.Congregacion).filter(models.Congregacion.id == congregacion_id).first()
            if congregacion_a_borrar:
                db.delete(congregacion_a_borrar)
                db.commit()

    return {"mensaje": "Orador y congregación vacía eliminados correctamente"}

@router.get("/api/oradores/{orador_id}/discursos")
def obtener_discursos_orador(orador_id: int, db: Session = Depends(get_db)):
    """Devuelve los datos y los números/títulos de los discursos que prepara este orador"""
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
    
    # Unificar todos los tipos de guiones
    nombre_limpio = str(nombre).replace('\u2013', '-').replace('\u2014', '-').replace('\u2011', '-')
    
    # Quitar tildes y espacios extra
    nfkd = unicodedata.normalize('NFKD', nombre_limpio)
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    limpio = sin_tildes.strip().title()
    
    lower_val = limpio.lower()
    
    # Solo rechazar si está vacío o es un guion suelto / texto nulo
    if lower_val in ['', 'nan', 'nat', 'none', '-', '--']:
        return "Local"
        
    # Filtrar palabras de cargos si aparecen
    if any(w in lower_val for w in ['coordinador', 'coordinadora', 'cargo']):
        return "Local"
        
    return limpio.rstrip(':').strip()


@router.get("/sincronizar-db-desde-excel")
def sincronizar_db_desde_excel(db: Session = Depends(get_db)):
    """Sincroniza limpiamente congregaciones, oradores, cargos, teléfonos y discursos desde el Excel evitando duplicados"""
    
 # Vaciar todo para empezar desde cero y eliminar duplicados acumulados
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
    """Lee el archivo Excel de bosquejos externo y actualiza los títulos en la base de datos"""
    
    archivo_bosquejos = "Titulos_discursos_publicos.xlsx"  # El nombre exacto de tu archivo
    
    if not os.path.exists(archivo_bosquejos):
        return {
            "status": "error", 
            "detalle": f"No se encuentra el archivo '{archivo_bosquejos}' en la carpeta del proyecto."
        }

    try:
        df_bosquejos = pd.read_excel(archivo_bosquejos)
        
        # Normalizar nombres de columnas para quitar tildes, puntos y espacios
        df_bosquejos.columns = df_bosquejos.columns.astype(str).str.strip().str.lower()
        df_bosquejos.columns = df_bosquejos.columns.str.replace('.', '', regex=False).str.replace('º', '', regex=False)
        
        # Buscar columnas flexibles
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
    """Actualiza los datos de un orador existente, incluyendo su congregación y discursos"""
    orador = db.query(models.Orador).filter(models.Orador.id == orador_id).first()
    
    if not orador:
        raise HTTPException(status_code=404, detail="Orador no encontrado")
    
    # Actualizar campos básicos si vienen en la petición
    if datos.nombre is not None:
        orador.nombre = datos.nombre.strip()
    if datos.telefono is not None:
        orador.telefono = datos.telefono.strip() if datos.telefono else None
    if datos.congregacion_id is not None:
        orador.congregacion_id = datos.congregacion_id
        
    # Si se envían discursos, actualizamos la relación (borramos los viejos y ponemos los nuevos)
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
    """Crea una nueva congregación o la devuelve si ya existe"""
    nombre_limpio = datos.nombre.strip()
    
    existe = db.query(models.Congregacion).filter(models.Congregacion.nombre.ilike(nombre_limpio)).first()
    if existe:
        return existe
        
    nueva = models.Congregacion(nombre=nombre_limpio)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


#Histórico de discursos por año

@router.get("/historico")
def obtener_historico_discursos(db: Session = Depends(get_db)):
    """Devuelve una matriz histórica de discursos por año basada en la planificación"""
    planificaciones = db.query(models.Planificacion).filter(
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


#LOGIN Y CREACIÓN DE USUARIOS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/auth/login")
def login(datos: schemas.LoginSchema, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    
    if not usuario or not pbkdf2_sha256.verify(datos.password, usuario.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
        
    return {
        "status": "success",
        "username": usuario.username,
        "rol": usuario.rol,
        "mensaje": "Login exitoso"
    }

@router.post("/auth/crear-usuario")
def crear_usuario(datos: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        
    hashed_pwd = pwd_context.hash(datos.password)
    nuevo_usuario = models.Usuario(
        username=datos.username.strip(),
        hashed_password=hashed_pwd,
        rol=datos.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {"status": "success", "mensaje": "Usuario creado correctamente"}
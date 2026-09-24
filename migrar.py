import os
import sys

# Agregamos la ruta raíz del proyecto al sistema de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importamos usando la ruta completa desde la raíz 'app'
from app.db.database import Base
from app.db.models import Congregacion, Orador, DiscursoOrador, Bosquejo, Planificacion, Usuario

# 1. Conexión a la base de datos ANTIGUA (SQLite)
SQLITE_URL = "sqlite:///./data/planning.db"
engine_sqlite = create_engine(SQLITE_URL)
SessionSQLite = sessionmaker(bind=engine_sqlite)
db_sqlite = SessionSQLite()

# 2. Conexión a la base de datos NUEVA (PostgreSQL en Docker)
POSTGRES_URL = "postgresql://admin:1234@localhost:5432/PlanningDiscursosDB"
engine_pg = create_engine(POSTGRES_URL)
SessionPG = sessionmaker(bind=engine_pg)
db_pg = SessionPG()

def migrar_datos():
    print("🚀 Iniciando migración de SQLite a PostgreSQL...")

    # Creamos las tablas en PostgreSQL si no existían
    Base.metadata.create_all(bind=engine_pg)

    try:
        # --- 1. MIGRAR CONGREGACIONES ---
        print("Migrando congregaciones...")
        for c in db_sqlite.query(Congregacion).all():
            if not db_pg.query(Congregacion).filter_by(id=c.id).first():
                db_pg.add(Congregacion(id=c.id, nombre=c.nombre))
        db_pg.commit()

        # --- 2. MIGRAR BOSQUEJOS ---
        print("Migrando bosquejos...")
        for b in db_sqlite.query(Bosquejo).all():
            if not db_pg.query(Bosquejo).filter_by(numero=b.numero).first():
                db_pg.add(Bosquejo(numero=b.numero, titulo=b.titulo))
        db_pg.commit()

        # --- 3. MIGRAR ORADORES ---
        print("Migrando oradores...")
        for o in db_sqlite.query(Orador).all():
            if not db_pg.query(Orador).filter_by(id=o.id).first():
                db_pg.add(Orador(
                    id=o.id,
                    nombre=o.nombre,
                    cargo=o.cargo,
                    es_coordinador=o.es_coordinador,
                    telefono=o.telefono,
                    email_jw=o.email_jw,
                    email_personal=o.email_personal,
                    congregacion_id=o.congregacion_id
                ))
        db_pg.commit()

        # --- 4. MIGRAR DISCURSOS DE ORADORES ---
        print("Migrando discursos de oradores...")
        for d in db_sqlite.query(DiscursoOrador).all():
            if not db_pg.query(DiscursoOrador).filter_by(id=d.id).first():
                db_pg.add(DiscursoOrador(
                    id=d.id,
                    numero_discurso=d.numero_discurso,
                    orador_id=d.orador_id
                ))
        db_pg.commit()

        # --- 5. MIGRAR PLANIFICACIÓN ---
        print("Migrando planificaciones...")
        for p in db_sqlite.query(Planificacion).all():
            if not db_pg.query(Planificacion).filter_by(id=p.id).first():
                db_pg.add(Planificacion(
                    id=p.id,
                    fecha=p.fecha,
                    id_orador=p.id_orador,
                    numero_bosquejo=p.numero_bosquejo,
                    estado_invitacion=p.estado_invitacion,
                    estado_confirmacion=p.estado_confirmacion,
                    fecha_envio=p.fecha_envio,
                    token_confirmacion=p.token_confirmacion,
                    es_evento_especial=p.es_evento_especial,
                    texto_evento=p.texto_evento
                ))
        db_pg.commit()

        # --- 6. MIGRAR USUARIOS ---
        print("Migrando usuarios...")
        for u in db_sqlite.query(Usuario).all():
            if not db_pg.query(Usuario).filter_by(id=u.id).first():
                db_pg.add(Usuario(
                    id=u.id,
                    username=u.username,
                    hashed_password=u.hashed_password,
                    rol=u.rol
                ))
        db_pg.commit()

        print("¡Migración completada con éxito absoluto! 🎉")

    except Exception as e:
        db_pg.rollback()
        print(f"❌ Error durante la migración: {e}")
    finally:
        db_sqlite.close()
        db_pg.close()

if __name__ == "__main__":
    migrar_datos()
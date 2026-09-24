import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Si existe una variable de entorno DATABASE_URL (la que pondrá Render), la usa. 
# Si no, usa la de tu Docker local.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://admin:1234@localhost:5432/PlanningDiscursosDB"
)

# Nota: Render a veces provee URLs que empiezan por "postgres://", 
# SQLAlchemy requiere "postgresql://", así que hacemos este pequeño ajuste por seguridad:
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Función generadora para obtener la sesión de la base de datos en las rutas"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
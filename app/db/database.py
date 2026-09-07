import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Creamos la carpeta data si no existe
os.makedirs("data", exist_ok=True)

# Indicamos que la base de datos se guardará en data/planning.db
DATABASE_URL = "sqlite:///./data/planning.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} # Requerido para SQLite en FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Función generadora para obtener la sesión de la base de datos en las rutas"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
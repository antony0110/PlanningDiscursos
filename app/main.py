import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.api.routes import router as api_router
from app.db.database import engine, Base, SessionLocal
from app.db import models

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Planning Discursos",
    description="Sistema de gestión de discursos públicos y oradores",
    version="1.0.0"
)

# Incluir las rutas de routes.py bajo el prefijo /api
app.include_router(api_router, prefix="/api")

# Configurar archivos estáticos
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home():
    html_path = "app/static/index.html"
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse("<h2>El archivo app/static/index.html no existe aún. Créalo para ver la interfaz.</h2>")

# @app.on_event("startup")
# def startup_event():
#     # 1. Crear las tablas si no existen
#     models.Base.metadata.create_all(bind=engine)
    
#     # 2. Comprobar si la base de datos está vacía para poblarla automáticamente
#     db = SessionLocal()
#     try:
#         total_registros = db.query(models.Planificacion).count()
#         if total_registros == 0:
#             print("🔄 Base de datos vacía detectada en el arranque. Importando datos desde Excel...")
            
#             # Importación local para evitar conflictos de rutas al arrancar
#             from Importar_datos import importar_archivo
            
#             if os.path.exists("PlanAnual2025_Limpio.xlsx"):
#                 importar_archivo("PlanAnual2025_Limpio.xlsx", 2025)
#             if os.path.exists("Planificacion_Procesada.xlsx"):
#                 importar_archivo("Planificacion_Procesada.xlsx", 2026)
#     except Exception as e:
#         print(f"⚠️ Error al auto-importar datos en el arranque: {e}")
#     finally:
#         db.close()


from fastapi.responses import FileResponse

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")
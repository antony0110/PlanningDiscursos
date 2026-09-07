import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.api.routes import router as api_router
from app.db.database import engine, Base

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


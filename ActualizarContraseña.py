import sys
import os

# Asegurar que el directorio actual esté en el path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
from app.db.database import SessionLocal
from app.db.models import Usuario  # Importado directamente desde la raíz

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

# Generar el hash exacto compatible para "admin123"
nuevo_hash = pwd_context.hash("admin123")

# Actualizar el usuario admin en la base de datos
admin_user = db.query(Usuario).filter(Usuario.username == "admin").first()
if admin_user:
    admin_user.hashed_password = nuevo_hash
    db.commit()
    print("¡Contraseña de admin actualizada con éxito!")
else:
    print("No se encontró el usuario admin.")

db.close()
from passlib.hash import pbkdf2_sha256
from app.db.database import SessionLocal, engine
from app.db import models

# Crea las tablas si no existen
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Pon aquí la contraseña que quieras usar
nueva_contrasena = "CongreAlgemesi"

usuario_existente = db.query(models.Usuario).filter(models.Usuario.username == "admin").first()

if not usuario_existente:
    # Si no existe, lo crea desde cero
    hashed_password = pbkdf2_sha256.hash(nueva_contrasena)
    nuevo_admin = models.Usuario(
        username="admin",
        hashed_password=hashed_password,
        rol="admin"
    )
    db.add(nuevo_admin)
    db.commit()
    print("¡Administrador creado con éxito!")
else:
    # Si ya existe, actualiza su contraseña con la nueva que hayas puesto
    usuario_existente.hashed_password = pbkdf2_sha256.hash(nueva_contrasena)
    db.commit()
    print("¡Contraseña del administrador actualizada con éxito!")

db.close()
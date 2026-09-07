from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
eliminados = db.query(models.Planificacion).delete()
db.commit()
db.close()
print(f"¡Se han borrado {eliminados} registros de planificación incorrectos. Base limpia!")
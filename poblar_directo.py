import pandas as pd
from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
archivo = "discursantes_limpio.xlsx"

try:
    df = pd.read_excel(archivo)
    df.columns = df.columns.astype(str).str.strip()
    
    for _, row in df.iterrows():
        nombre_excel = str(row.get('Nombre', '')).strip()
        if not nombre_excel or nombre_excel.lower() == 'nan':
            continue

        cong_nombre = str(row.get('Congregac', row.get('Congregación', 'Local'))).strip()
        cargo_val = str(row.get('Cargo', '')).strip()
        tel_val = str(row.get('Telefono', row.get('Teléfono', ''))).strip()
        discursos_val = row.get('Discursos', '')

        # 1. Asegurar Congregación
        congregacion = db.query(models.Congregacion).filter(models.Congregacion.nombre.ilike(cong_nombre)).first()
        if not congregacion:
            congregacion = models.Congregacion(nombre=cong_nombre)
            db.add(congregacion)
            db.commit()
            db.refresh(congregacion)

        # 2. Buscar orador por nombre parcial o teléfono
        orador = db.query(models.Orador).filter(models.Orador.nombre.ilike(f"%{nombre_excel}%")).first()
        if not orador and tel_val and tel_val.lower() != 'nan':
            orador = db.query(models.Orador).filter(models.Orador.telefono == tel_val).first()

        if orador:
            orador.congregacion_id = congregacion.id
            if cargo_val and cargo_val.lower() != 'nan' and cargo_val != '-':
                orador.cargo = cargo_val
            if tel_val and tel_val.lower() != 'nan':
                orador.telefono = tel_val
        else:
            orador = models.Orador(
                nombre=nombre_excel,
                cargo=cargo_val if cargo_val and cargo_val.lower() != 'nan' and cargo_val != '-' else None,
                telefono=tel_val if tel_val.lower() != 'nan' else None,
                congregacion_id=congregacion.id
            )
            db.add(orador)
            db.commit()
            db.refresh(orador)

        # 3. Sincronizar discursos
        db.query(models.DiscursoOrador).filter(models.DiscursoOrador.orador_id == orador.id).delete()
        if not pd.isna(discursos_val):
            for p in str(discursos_val).replace(';', ',').split(','):
                p_clean = ''.join(filter(str.isdigit, p))
                if p_clean.isdigit():
                    num = int(p_clean)
                    if not db.query(models.DiscursoOrador).filter_by(orador_id=orador.id, numero_discurso=num).first():
                        db.add(models.DiscursoOrador(orador_id=orador.id, numero_discurso=num))

    db.commit()
    print("¡Reparación y sincronización completadas con éxito!")

except Exception as e:
    print(f"❌ Error: {e}")

db.close()
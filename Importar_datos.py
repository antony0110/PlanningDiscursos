import pandas as pd
import unicodedata
from app.db.database import engine, Base, SessionLocal
from app.db.models import Congregacion, Orador, DiscursoOrador

def normalizar(texto: str) -> str:
    """Limpia el texto para comparar congregaciones ignorando tildes, espacios y casos especiales."""
    if not texto: return ""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    sin_tildes = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return sin_tildes.lower().replace("'", "").replace("´", "").replace("`", "").strip()

def cargar_excel_a_db():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Limpiar base de datos antes de importar
    db.query(DiscursoOrador).delete()
    db.query(Orador).delete()
    db.query(Congregacion).delete()
    db.commit()

    ruta_excel = "Coordinadores_limpio.xlsx"
    print(f"Leyendo archivo {ruta_excel}...")
    df = pd.read_excel(ruta_excel)
    df.columns = df.columns.astype(str).str.strip()

    # El caché guardará la versión normalizada como llave
    cache_congregaciones = {}

    for _, row in df.iterrows():
        # Usamos el nombre exacto de la columna que aparece en tu imagen: "Congregación"
        nombre_raw = str(row["Congregación"]).strip() if pd.notna(row.get("Congregación")) else "Desconocida"
        clave_norm = normalizar(nombre_raw)
        
        # 2. Guardar o reutilizar congregación usando la clave normalizada
        if clave_norm not in cache_congregaciones:
            todas_congres = db.query(Congregacion).all()
            cong_encontrada = None
            for c in todas_congres:
                if normalizar(c.nombre) == clave_norm:
                    cong_encontrada = c
                    break
            
            if not cong_encontrada:
                cong_encontrada = Congregacion(nombre=nombre_raw)
                db.add(cong_encontrada)
                db.flush()
                
            cache_congregaciones[clave_norm] = cong_encontrada.id

        cong_id = cache_congregaciones[clave_norm]

        # 3. Crear Orador de forma segura comprobando las posibles variantes de columna
        es_coord = False
        if "Coordinador" in df.columns and pd.notna(row.get("Coordinador")):
            es_coord = True if str(row["Coordinador"]).strip().lower() == "sí" else False
        elif "Coord" in df.columns and pd.notna(row.get("Coord")):
            es_coord = True if str(row["Coord"]).strip().lower() == "sí" else False

        orador = Orador(
            nombre=str(row["Nombre"]).strip() if pd.notna(row.get("Nombre")) else "",
            cargo=str(row["Cargo"]).strip() if pd.notna(row.get("Cargo")) else "",
            es_coordinador=es_coord,
            telefono=str(row["Telefono"]).strip() if pd.notna(row.get("Telefono")) else "",
            email_jw=str(row["Email_JW"]).strip() if pd.notna(row.get("Email_JW")) else "",
            email_personal=str(row["Email_Personal"]).strip() if pd.notna(row.get("Email_Personal")) else "",
            congregacion_id=cong_id
        )
        db.add(orador)
        db.flush()

        # 4. Insertar Discursos
        col_disc = next((c for c in df.columns if 'discurso' in c.lower()), None)
        if col_disc and pd.notna(row.get(col_disc)):
            discursos_lista = str(row[col_disc]).split(",")
            for disc in discursos_lista:
                disc_clean = disc.strip()
                if disc_clean.isdigit():
                    discurso_obj = DiscursoOrador(
                        numero_discurso=int(disc_clean),
                        orador_id=orador.id
                    )
                    db.add(discurso_obj)

    db.commit()
    db.close()
    print("¡Proceso completado! La base de datos está limpia, sin duplicados y con las columnas correctas.")

if __name__ == "__main__":
    cargar_excel_a_db()
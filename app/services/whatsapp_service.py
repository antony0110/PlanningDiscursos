import pandas as pd
import warnings

warnings.filterwarnings('ignore')

RUTA_ORIGEN = "data/Coordinadores ESP-V-03.xlsx"
RUTA_DESTINO = "data/discursantes_limpio.xlsx"

def limpiar_y_exportar_excel():
    try:
        # 1. Leer el archivo original sin asumir cabeceras
        df = pd.read_excel(RUTA_ORIGEN, header=None)
        
        discursantes = []
        congregacion_actual = "Sin Congregación"

        # 2. Recorrer fila por fila para organizar la información
        for idx, row in df.iterrows():
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
            col1 = str(row[1]).strip() if pd.notna(row[1]) else ""
            
            # Si la columna 0 tiene texto y no es "Coordinador", es el nombre de la congregación
            if col0 and col0 != "Coordinador" and col0.lower() != "nan":
                congregacion_actual = col0
            
            # Si la columna 1 tiene un nombre, extraemos sus datos
            if col1 and col1.lower() != "nombre" and col1.lower() != "nan":
                es_coordinador = (col0 == "Coordinador")
                cargo = str(row[2]).strip() if pd.notna(row[2]) and str(row[2]).lower() != "nan" else ""
                telefono = str(row[3]).strip() if pd.notna(row[3]) and str(row[3]).lower() != "nan" else ""
                email_jw = str(row[4]).strip() if pd.notna(row[4]) and str(row[4]).lower() != "nan" else ""
                email_personal = str(row[5]).strip() if pd.notna(row[5]) and str(row[5]).lower() != "nan" else ""
                
                # Juntar los números de discursos de las columnas siguientes
                discursos = []
                for c in range(6, len(row)):
                    if pd.notna(row[c]):
                        val = str(row[c]).strip()
                        if val.endswith('.0'):
                            val = val[:-2]
                        if val and val.lower() != "nan":
                            discursos.append(val)
                            
                discursantes.append({
                    "Congregacion": congregacion_actual,
                    "Nombre": col1,
                    "Cargo": cargo,
                    "Coordinador": "Sí" if es_coordinador else "No",
                    "Telefono": telefono,
                    "Email_JW": email_jw,
                    "Email_Personal": email_personal,
                    "Discursos": ", ".join(discursos)
                })

        # 3. Crear una tabla limpia y guardarla en un nuevo Excel
        df_limpio = pd.DataFrame(discursantes)
        df_limpio.to_excel(RUTA_DESTINO, index=False)
        
        print(f"¡Éxito! Se han procesado {len(df_limpio)} discursantes.")
        print(f"Nuevo archivo guardado en: {RUTA_DESTINO}\n")
        print("--- VISTA PREVIA DE LOS PRIMEROS DATOS ---")
        print(df_limpio[["Congregacion", "Nombre", "Cargo", "Telefono", "Discursos"]].head())

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    limpiar_y_exportar_excel()
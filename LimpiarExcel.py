import os
import pandas as pd

ARCHIVO_SUCIO = "PlanAnual2025.xlsx"
ARCHIVO_LIMPIO = "PlanAnual2025_Limpio.xlsx"

def generar_excel_limpio():
    if not os.path.exists(ARCHIVO_SUCIO):
        print(f"❌ No se encuentra el archivo '{ARCHIVO_SUCIO}' en la raíz del proyecto.")
        return

    print("Leyendo el archivo original sin cabecera fija...")
    df_raw = pd.read_excel(ARCHIVO_SUCIO, header=None)
    
    # Buscar en qué fila se encuentra la palabra "Fecha" de forma totalmente segura
    fila_cabecera = None
    for index, row in df_raw.iterrows():
        if any('fecha' in str(val).lower() for val in row):
            fila_cabecera = index
            break
            
    if fila_cabecera is None:
        print("❌ No se ha podido localizar la fila de cabecera que contiene 'Fecha'.")
        return
        
    print(f"✅ Cabecera encontrada automáticamente en la fila {fila_cabecera}")
    
    # Volver a leer el Excel usando la fila correcta como cabecera
    df = pd.read_excel(ARCHIVO_SUCIO, header=fila_cabecera)
    
    # Limpiar espacios y caracteres raros de las columnas
    df.columns = df.columns.astype(str).str.strip().str.encode('ascii', 'ignore').str.decode('ascii')
    print("📋 Columnas detectadas:", df.columns.tolist())

    # Identificar la columna de fecha
    col_fecha = next((col for col in df.columns if 'fecha' in col.lower()), None)
    if not col_fecha:
        print("❌ No se ha podido encontrar la columna de 'Fecha'.")
        return

    # Eliminar filas vacías en la fecha
    df = df.dropna(subset=[col_fecha])
    
    # Convertir a formato fecha válido y limpiar errores
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
    df = df.dropna(subset=[col_fecha])

    # Ordenar por fecha cronológicamente
    df = df.sort_values(by=col_fecha)

    # Limpiar espacios en blanco en todas las celdas de texto
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(['nan', 'None', 'NAT', 'NaT'], '')

    # Guardar el archivo limpio
    df.to_excel(ARCHIVO_LIMPIO, index=False)
    print(f"🎉 ¡Listo! Se ha generado el archivo limpio: '{ARCHIVO_LIMPIO}' con {len(df)} registros válidos.")

if __name__ == "__main__":
    generar_excel_limpio()
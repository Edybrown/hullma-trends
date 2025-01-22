import pandas as pd
import os

def calcular_funding_rate(df):
    """Calcula el funding rate a partir de los datos OHLCV."""
    if 'ohlcv_close_BTCUSDT_PERP.A' in df.columns and 'ohlcv_close_BTCUSDT.A' in df.columns:
        df['funding_rate'] = (df['ohlcv_close_BTCUSDT_PERP.A'] - df['ohlcv_close_BTCUSDT.A']) / df['ohlcv_close_BTCUSDT.A']
    else:
        print("Columnas 'ohlcv_close_BTCUSDT_PERP.A' o 'ohlcv_close_BTCUSDT.A' no encontradas. No se puede calcular el funding rate.")
        df['funding_rate'] = None #Añadir la columna aunque sea vacia para no generar errores
    return df

def procesar_archivos_csv(carpeta="coinalyze_data"):
    """Procesa los archivos CSV en la carpeta especificada."""
    try:
        archivos_csv = [archivo for archivo in os.listdir(carpeta) if archivo.startswith("datos_") and archivo.endswith(".csv")]
        if not archivos_csv:
            print(f"No se encontraron archivos CSV en la carpeta '{carpeta}'.")
            return

        for archivo in archivos_csv:
            ruta_completa = os.path.join(carpeta, archivo)
            print(f"Procesando archivo: {archivo}")
            try:
                df = pd.read_csv(ruta_completa)
                df = calcular_funding_rate(df)
                df.to_csv(ruta_completa, index=False) #Sobreescribir el archivo original
                print(f"Funding rate calculado y guardado en: {ruta_completa}")
            except pd.errors.ParserError as e:
                print(f"Error al leer el archivo CSV {archivo}: {e}")
            except Exception as e:
                print(f"Error inesperado al procesar {archivo}: {e}")
    except FileNotFoundError:
        print(f"La carpeta '{carpeta}' no existe.")

# Ejecutar el procesamiento
procesar_archivos_csv()

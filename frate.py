import pandas as pd
import os
import re

def calcular_funding_rate(df):
    """Calcula el funding rate a partir de los datos OHLCV."""
    try:
        # Usar expresiones regulares para encontrar las columnas de cierre
        perp_close_col = next(col for col in df.columns if re.match(r"ohlcv_close_.+_PERP\.A", col))
        spot_close_col = next(col for col in df.columns if re.match(r"ohlcv_close_.+\.A", col))

        df['funding_rate'] = (df[perp_close_col] - df[spot_close_col]) / df[spot_close_col]
    except StopIteration:
        print("No se encontraron las columnas de cierre de futuros o spot. No se puede calcular el funding rate.")
        df['funding_rate'] = None
    except ZeroDivisionError:
        print("Error de división por cero. El precio spot es cero. No se puede calcular el funding rate.")
        df['funding_rate'] = None
    except Exception as e:
        print(f"Error inesperado al calcular el funding rate: {e}")
        df['funding_rate'] = None
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
                df.to_csv(ruta_completa, index=False)
                print(f"Funding rate calculado y guardado en: {ruta_completa}")
            except pd.errors.ParserError as e:
                print(f"Error al leer el archivo CSV {archivo}: {e}")
            except Exception as e:
                print(f"Error inesperado al procesar {archivo}: {e}")
    except FileNotFoundError:
        print(f"La carpeta '{carpeta}' no existe.")

# Ejecutar el procesamiento
procesar_archivos_csv()

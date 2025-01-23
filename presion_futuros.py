import pandas as pd
import os
import math
import numpy as np

# Directorio donde están los archivos CSV
data_directory = "coinalyze_data"

# Lista de archivos CSV en el directorio
files = [f for f in os.listdir(data_directory) if f.endswith('.csv')]

# Función para calcular el Indicador de Presión Direccional Modificado
def calcular_indicador(funding_rate, long_short_ratio, oi_total, longs_percentage):
    if funding_rate is None or long_short_ratio is None or oi_total is None or longs_percentage is None:
        return np.nan  # Devolver NaN si algún valor es None

    # Evitar división por cero y valores cero en OI
    long_short_ratio = max(long_short_ratio, 0.0001)
    oi_total = max(oi_total, 1)

    funding_rate_abs = abs(funding_rate)

    # Cálculo del indicador (sin la modificación innecesaria con la raiz y el logaritmo)
    desequilibrio = abs(longs_percentage - 50) / 50
    indicador = funding_rate_abs * oi_total * desequilibrio

    return indicador

# Procesar cada archivo CSV
for file in files:
    file_path = os.path.join(data_directory, file)
    try:
        df = pd.read_csv(file_path)

        # Extraer las columnas necesarias, manejando posibles KeyError
        try:
            funding_rate = df['funding_rate']
            long_short_ratio = df['long_short_ratio_long_short_ratio_']
            oi_total = df['open_interest_oi_open_']
            longs_percentage = df['long_short_ratio_longs_percentage_']
        except KeyError as e:
            print(f"Error: No se encontró la columna {e} en el archivo {file}. Saltando este archivo.")
            continue # Saltar al siguiente archivo si hay un error de columna

        # Calcular el indicador, manejando posibles errores en el cálculo
        try:
            df['presion_direccional'] = [
                calcular_indicador(f, lsr, oi, lp) for f, lsr, oi, lp in zip(funding_rate, long_short_ratio, oi_total, longs_percentage)
            ]
        except TypeError as e:
            print(f"Error de tipo en el calculo del indicador en {file}: {e}")
            print("Revisar los tipos de datos de las columnas funding_rate, long_short_ratio, oi_total y longs_percentage")
            continue

        # Sobrescribir el archivo, eliminando filas con NaN en la nueva columna
        df = df.dropna(subset=['presion_direccional'])
        df.to_csv(file_path, index=False)
        print(f"Archivo actualizado: {file_path}")
    except pd.errors.ParserError as e:
        print(f"Error al leer el archivo CSV {file}: {e}")
    except Exception as e:
        print(f"Error inesperado al procesar {file}: {e}")

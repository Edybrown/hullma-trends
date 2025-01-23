import pandas as pd
import os
import math

# Directorio donde están los archivos CSV
data_directory = "coinalyze_data"

# Lista de archivos CSV en el directorio
files = [f for f in os.listdir(data_directory) if f.endswith('.csv')]

# Función para calcular el Indicador de Presión Direccional Modificado
def calcular_indicador(funding_rate, long_short_ratio, oi_total, longs_percentage):
    # Evitar valores cero en OI
    oi_total = max(oi_total, 1)  # Prevenir que OI sea 0, establecer en 1 si es muy bajo

    # Asegurémonos de que el funding_rate esté bien procesado
    funding_rate_abs = abs(funding_rate)

    # Evitar valores extremos con un logaritmo de OI más seguro
    term1 = funding_rate_abs / (long_short_ratio + 0.0001)

    # Calcular el logaritmo de OI con una pequeña constante si es necesario
    term2 = math.sqrt(oi_total) / (math.log(oi_total + 1) + 1)

    # Asegurarnos de que los valores de longs_percentage estén entre 0 y 100
    term3 = 1 + abs(longs_percentage - 50) / 50

    # Indicador de Presión Direccional
    indicador = term1 * term2 * term3
    return indicador

# Procesar cada archivo CSV
for file in files:
    # Leer el archivo CSV
    file_path = os.path.join(data_directory, file)
    df = pd.read_csv(file_path)

    # Extraer las columnas necesarias
    funding_rate = df['funding_rate']
    long_short_ratio = df['long_short_ratio_long_short_ratio_']
    oi_total = df['open_interest_oi_open_']  # OI Total
    longs_percentage = df['long_short_ratio_longs_percentage_']

    # Calcular el indicador de presión direccional para cada fila
    df['presion_direccional'] = [
        calcular_indicador(f, lsr, oi, lp) for f, lsr, oi, lp in zip(funding_rate, long_short_ratio, oi_total, longs_percentage)
    ]

    # Sobrescribir el archivo con el nuevo indicador agregado como columna
    df.to_csv(file_path, index=False)
    print(f"Archivo actualizado: {file_path}")

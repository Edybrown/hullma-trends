import pandas as pd
import os
import math

# Directorio donde están los archivos CSV
data_directory = "coinalyze_data"

# Lista de archivos CSV en el directorio
files = [f for f in os.listdir(data_directory) if f.endswith('.csv')]

# Función para calcular el Indicador de Presión Direccional Mejorado
def calcular_indicador(funding_rate, long_short_ratio, oi_total, longs_percentage):
    # Primer término (Funding Rate y Long/Short Ratio)
    term1 = abs(funding_rate) / (long_short_ratio + 0.0001)

    # Segundo término (Raíz cuadrada de OI y logaritmo)
    term2 = math.sqrt(oi_total) / (math.log(oi_total) + 1)

    # Tercer término (Longs Percentage)
    term3 = 1 + abs(longs_percentage - 50) / 50

    # Indicador de Presión Direccional Mejorado
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

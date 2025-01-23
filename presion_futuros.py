import pandas as pd
import numpy as np
import os

# Función para calcular el nuevo indicador de desequilibrio (versión corregida)
def calcular_desequilibrio(funding_rate, longs_percentage):
    # Calcular el desequilibrio L/S
    LS_desequilibrio = longs_percentage - (100 - longs_percentage)  # Simplificado: %Largos - %Cortos
    
    # Funding Rate anualizado (asumiendo que viene por periodo de 8h)
    funding_rate_anualizado = (1 + funding_rate)**1095 - 1

    # Calcular el indicador
    indicador = (LS_desequilibrio + (funding_rate_anualizado*100)) / 2
    return indicador

# Ruta a la carpeta donde están los archivos CSV
carpeta_csv = 'coinalyze_data'

# Iteramos sobre todos los archivos CSV en la carpeta
for archivo in os.listdir(carpeta_csv):
    if archivo.endswith('.csv'):
        # Cargar el CSV
        ruta_csv = os.path.join(carpeta_csv, archivo)
        df = pd.read_csv(ruta_csv)

        # Asegurarse de que las columnas necesarias existen
        columnas_necesarias = [
            'funding_rate',
            'long_short_ratio_longs_percentage_'
        ]

        if all(col in df.columns for col in columnas_necesarias):
            # Aplicar la función para calcular el nuevo indicador de desequilibrio
            df['desequilibrio_OI'] = df.apply(
                lambda row: calcular_desequilibrio(
                    row['funding_rate'],
                    row['long_short_ratio_longs_percentage_']
                ), axis=1
            )

            # Guardar el DataFrame con la nueva columna en el mismo archivo CSV
            df.to_csv(ruta_csv, index=False)
            print(f"El indicador se ha calculado y agregado correctamente al archivo: {archivo}")
        else:
            print(f"Faltan algunas columnas necesarias en el archivo: {archivo}")

import pandas as pd
import numpy as np
import os

# Función para calcular el indicador de presión direccional modificado
def calcular_presion_direccional(funding_rate, long_short_ratio, oi_total, longs_percentage):
    # Fórmula del indicador con Funding Rate anualizado
    indicador = (funding_rate / (long_short_ratio + 0.0001)) * np.log(oi_total) * abs((longs_percentage - 50) / 50)
    return indicador

# Ruta a la carpeta donde están los archivos CSV
carpeta_csv = 'coinalyze_data'  # Asegúrate de ajustar esta ruta si es necesario

# Iteramos sobre todos los archivos CSV en la carpeta
for archivo in os.listdir(carpeta_csv):
    if archivo.endswith('.csv'):
        # Cargar el CSV
        ruta_csv = os.path.join(carpeta_csv, archivo)
        df = pd.read_csv(ruta_csv)
        
        # Asegurarse de que las columnas necesarias existen
        if all(col in df.columns for col in ['funding_rate', 'long_short_ratio_long_short_ratio_', 'open_interest_oi_open_', 'long_short_ratio_longs_percentage_']):
            
            # Convertir el Funding Rate en un valor anualizado
            # Suponiendo que el funding_rate está en formato mensual, multiplicamos por 12 para anualizarlo
            df['funding_rate_annualizado'] = df['funding_rate'] * 12  # Si el funding_rate está en base mensual
            
            # Aplicar la función para calcular el indicador de presión direccional modificado
            df['presion_direccional'] = df.apply(
                lambda row: calcular_presion_direccional(
                    row['funding_rate_annualizado'], 
                    row['long_short_ratio_long_short_ratio_'], 
                    row['open_interest_oi_open_'], 
                    row['long_short_ratio_longs_percentage_']
                ), axis=1
            )
            
            # Guardar el DataFrame con la nueva columna en el mismo archivo CSV
            df.to_csv(ruta_csv, index=False)
            print(f"El indicador se ha calculado y agregado correctamente al archivo: {archivo}")
        else:
            print(f"Faltan algunas columnas necesarias en el archivo: {archivo}")

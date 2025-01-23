import pandas as pd
import numpy as np
import os

# Función para calcular el nuevo indicador de desequilibrio
# Basado en el funding rate, el long/short ratio, el open interest y la proporción de longs
# Este indicador combina las fórmulas discutidas anteriormente

def calcular_desequilibrio(funding_rate, long_short_ratio, oi_total, longs_percentage):
    # Pesos para los componentes del indicador
    w1, w2, w3 = 0.5, 0.3, 0.2

    # Calcular los componentes del indicador
    delta_oi_percent = np.log(oi_total + 1)  # Escalamos con logaritmo
    LS_desequilibrio = (longs_percentage - 50) / 50  # Desequilibrio en L/S ratio, entre -1 y 1
    funding_rate_contrib = funding_rate  # Funding rate ya anualizado

    # Combinar los componentes usando los pesos
    indicador = (delta_oi_percent * w1) + (LS_desequilibrio * w2 * 100) + (funding_rate_contrib * w3 * 100)
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
        columnas_necesarias = [
            'funding_rate', 
            'long_short_ratio_long_short_ratio_', 
            'open_interest_oi_open_', 
            'long_short_ratio_longs_percentage_'
        ]

        if all(col in df.columns for col in columnas_necesarias):

            # Convertir el Funding Rate en un valor anualizado
            # Suponiendo que el funding_rate está en formato mensual, multiplicamos por 12 para anualizarlo
            df['funding_rate_annualizado'] = df['funding_rate'] * 12

            # Aplicar la función para calcular el nuevo indicador de desequilibrio
            df['desequilibrio_OI'] = df.apply(
                lambda row: calcular_desequilibrio(
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

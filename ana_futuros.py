import pandas as pd
import numpy as np
import os
import math

# Función para calcular el Weighted Moving Average (WMA)
def calcular_wma(serie, periodo):
    pesos = np.arange(1, periodo + 1)
    return serie.rolling(periodo).apply(lambda valores: np.dot(valores, pesos) / pesos.sum(), raw=True)

# Función para calcular el Hull Moving Average (HMA)
def calcular_hma(serie, periodo=12):
    if len(serie) < periodo:
        print(f"Datos insuficientes para calcular la HMA con periodo {periodo}.")
        return pd.Series(index=serie.index, dtype='float64')

    wma_n2 = calcular_wma(serie, periodo // 2)
    wma_n = calcular_wma(serie, periodo)
    hma_calculada = calcular_wma(2 * wma_n2 - wma_n, int(math.sqrt(periodo)))
    return hma_calculada

# Procesar un archivo CSV
def procesar_archivo(ruta_csv, temporalidades):
    try:
        df = pd.read_csv(ruta_csv, parse_dates=['fecha_hora'])
    except Exception as e:
        print(f"Error al leer el archivo {os.path.basename(ruta_csv)}: {e}")
        return

    columnas_necesarias = ['ohlcv_close_BTCUSDT_PERP.A', 'fecha_hora', 'desequilibrio_OI']
    if not all(col in df.columns for col in columnas_necesarias):
        print(f"El archivo {os.path.basename(ruta_csv)} no contiene las columnas necesarias.")
        return

    df.set_index('fecha_hora', inplace=True)

    for temporalidad in temporalidades:
        df_resampled = df.resample(temporalidad).last()
        if df_resampled.empty or len(df_resampled) < 12:
            print(f"Datos insuficientes para la temporalidad {temporalidad} en el archivo {os.path.basename(ruta_csv)}.")
            continue

        df_resampled['hma_12'] = calcular_hma(df_resampled['ohlcv_close_BTCUSDT_PERP.A'])
        df_resampled.dropna(inplace=True)

        if df_resampled.empty:
            print(f"Sin datos válidos después de calcular la HMA para {temporalidad} en {os.path.basename(ruta_csv)}.")
            continue

        df_resampled['cruce'] = np.sign(df_resampled['hma_12'].diff())
        analizar_cruces(df_resampled, os.path.basename(ruta_csv), temporalidad)

# Analizar los cruces y calcular estadísticas
def analizar_cruces(df, nombre_archivo, temporalidad):
    resultados = {'Alcista': {'positivos': [], 'negativos': []}, 'Bajista': {'positivos': [], 'negativos': []}}

    for i in range(1, len(df)):
        if df['cruce'].iloc[i] == 1:  # Cruce Alcista
            desequilibrio = df['desequilibrio_OI'].iloc[i - 1]
            if desequilibrio > 0:
                resultados['Alcista']['positivos'].append(desequilibrio)
            elif desequilibrio < 0:
                resultados['Alcista']['negativos'].append(desequilibrio)
        elif df['cruce'].iloc[i] == -1:  # Cruce Bajista
            desequilibrio = df['desequilibrio_OI'].iloc[i - 1]
            if desequilibrio > 0:
                resultados['Bajista']['positivos'].append(desequilibrio)
            elif desequilibrio < 0:
                resultados['Bajista']['negativos'].append(desequilibrio)

    # Mostrar resultados
    for tipo_cruce, datos in resultados.items():
        print(f"{nombre_archivo} ({temporalidad}): Cruce {tipo_cruce}")
        for signo, valores in datos.items():
            if valores:
                print(f"  {signo.capitalize()}s - Cantidad: {len(valores)}, Promedio: {np.mean(valores):.2f}%")
            else:
                print(f"  {signo.capitalize()}s - Sin valores registrados.")
        print()

# Directorio de archivos CSV
carpeta_csv = 'coinalyze_data'
os.makedirs(carpeta_csv, exist_ok=True)

# Temporalidades para el resampleo
temporalidades = ['1h', '4h', '1d']

# Procesar cada archivo CSV
for archivo in os.listdir(carpeta_csv):
    if archivo.endswith('.csv'):
        print(f"Procesando archivo: {archivo}")
        procesar_archivo(os.path.join(carpeta_csv, archivo), temporalidades)

print("Proceso completado.")


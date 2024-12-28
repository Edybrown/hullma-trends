import requests
import pandas as pd
import time
import datetime
import os
import talib

def obtener_ohlc_kraken(pair, interval, since=None):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    if since:
        url += f"&since={since}"
    retries = 3
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data['error']:
                print(f"Error de Kraken: {data['error']}")
                return None
            if not data['result']:
                print("No hay datos disponibles para este intervalo.")
                return None
            df = pd.DataFrame(data['result'][pair], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            df = df.astype(float)
            return df
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos de Kraken: {e}")
            time.sleep(5)  # Esperar antes de reintentar
    print("Número máximo de reintentos alcanzado.")
    return None

def guardar_dataframe(df, filename):
    if df is not None:
        try:
            df.to_csv(filename)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("No hay datos para guardar.")

def obtener_y_guardar_multiples_temporalidades(pair, desde, carpeta="data"):
    # Crear la carpeta si no existe
    os.makedirs(carpeta, exist_ok=True)
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    for interval, filename_suffix in temporalidades.items():
        print(f"Obteniendo datos para el intervalo de {filename_suffix}...")
        df = obtener_ohlc_kraken(pair, interval, since=desde)
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        guardar_dataframe(df, filename)

# Ejemplo de uso:
pair = "XBTUSDT"  # Par BTC/USDT en Kraken
desde = datetime.datetime(2023, 1, 1).timestamp()
carpeta_datos = "datos_BTC" #Nombre de la carpeta donde se guardaran los archivos

obtener_y_guardar_multiples_temporalidades(pair, desde, carpeta_datos)

print("Proceso completado.")

# (Las funciones obtener_ohlc_kraken y guardar_dataframe del código anterior se mantienen igual)

def actualizar_dataframe(df, pair, interval):
    if df.empty:  # Si el DataFrame está vacío, obtener datos desde el inicio
        since = None
    else:
        last_timestamp = int(df.index[-1].timestamp()) + 1 #Obtener el ultimo timestamp y sumarle 1 segundo para evitar duplicados
        since = last_timestamp

    nuevos_datos = obtener_ohlc_kraken(pair, interval, since)

    if nuevos_datos is not None:
        if not nuevos_datos.empty: #Verificar si se obtuvieron nuevos datos
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')] #Eliminar duplicados en el indice
            return df_actualizado
        else:
            print(f"No hay nuevos datos para el intervalo {interval}")
            return df
    else:
        print(f"Error al obtener nuevos datos para el intervalo {interval}")
        return df

def actualizar_archivos(pair, carpeta="datos_BTC"):
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    for interval, filename_suffix in temporalidades.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        try:
            df = pd.read_csv(filename, index_col='time', parse_dates=True)
        except FileNotFoundError:
            print(f"Archivo {filename} no encontrado. Creando archivo nuevo.")
            df = pd.DataFrame()
        df = actualizar_dataframe(df, pair, interval)
        guardar_dataframe(df, filename)

# Ejemplo de uso (bucle principal):
pair = "XBTUSDT"
carpeta_datos = "datos_BTC"
frecuencia_actualizacion = 60  # Actualizar cada 60 segundos (1 minuto)

while True:
    print("Actualizando datos...")
    actualizar_archivos(pair, carpeta_datos)
    print(f"Datos actualizados. Esperando {frecuencia_actualizacion} segundos...")
    time.sleep(frecuencia_actualizacion)


import pandas as pd
import os

def leer_y_procesar_csv(ruta_archivo):
    """Lee un archivo CSV, lo imprime y realiza el procesamiento (ejemplo)."""
    try:
        print(f"Intentando leer el archivo: {ruta_archivo}")
        df = pd.read_csv(ruta_archivo, index_col='time', parse_dates=True,
                         dtype={'open': float, 'high': float, 'low': float, 'close': float, 'vwap': float, 'volume': float, 'count': float})

        print(f"DataFrame leído (primeras 5 filas):\n{df.head(5).to_string()}")
        print(f"Tipos de datos:\n{df.dtypes}")

        if df.empty:
            print(f"DataFrame vacío en {ruta_archivo}. No se puede procesar.")
            return None #Devuelve None si el DataFrame está vacío

        if not all(col in df.columns for col in ['open', 'close']):
            print(f"ERROR: Faltan columnas 'open' o 'close' en {ruta_archivo}. No se puede calcular la diferencia.")
            return None #Devuelve None si faltan las columnas necesarias

        df['Diferencia'] = df['close'] - df['open'] #Calcula la diferencia
        print(f"Diferencias calculadas (primeras 5):\n{df['Diferencia'].head().to_string()}")
        return df #Devuelve el DataFrame procesado

    except FileNotFoundError:
        print(f"ERROR: Archivo no encontrado en la ruta: {ruta_archivo}")
        return None
    except pd.errors.ParserError as e:
        print(f"ERROR al leer el CSV: {e}")
        return None
    except KeyError as e:
        print(f"ERROR de clave (posible problema con el índice o columnas): {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error general: {e}")
        return None

def main(): #Función main
    print("Iniciando el bot...")
    directorio_script_bot = os.path.dirname(os.path.abspath(__file__))
    nombre_archivo = "XBTUSDT_15m.csv"
    ruta_completa = os.path.join(directorio_script_bot, "datos_BTC", nombre_archivo)
    print(f"Ruta completa al archivo (desde el bot): {ruta_completa}")

    dataframe_procesado = leer_y_procesar_csv(ruta_completa) #Llama a la función de lectura y guarda el resultado
    if dataframe_procesado is not None: #Verifica si se obtuvo un DataFrame
        #Aquí puedes usar el dataframe_procesado para lo que necesites en tu bot
        print("DataFrame procesado correctamente. Continuando con la lógica del bot...")
    else:
        print("No se pudo procesar el DataFrame. Deteniendo el bot.")
        return #Sale de la función main si no se pudo procesar el DataFrame

    print("Bot en ejecución (simulado)...")
    while True:
        print("Bot haciendo cosas...")
        time.sleep(5)

if __name__ == "__main__": #Condicional para ejecutar la función main
    main()

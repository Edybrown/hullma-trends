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
    """Lee un archivo CSV, lo imprime (opcional) y lo procesa."""
    try:
        print(f"[leer_y_procesar_csv] Intentando leer el archivo: {ruta_archivo}") #Mensaje adicional
        if not os.path.exists(ruta_archivo): #Verifica si el archivo existe ANTES de intentar leerlo
            print(f"[leer_y_procesar_csv] ERROR: El archivo NO existe en la ruta: {ruta_archivo}")
            return None

        print(f"[leer_y_procesar_csv] Archivo EXISTE. Procediendo con la lectura...") #Mensaje adicional
        df = pd.read_csv(ruta_archivo, index_col='time', parse_dates=True,
                         dtype={'open': float, 'high': float, 'low': float, 'close': float, 'vwap': float, 'volume': float, 'count': float})

        print(f"[leer_y_procesar_csv] DataFrame leído (primeras 5 filas):\n{df.head(5).to_string()}")
        print(f"[leer_y_procesar_csv] Tipos de datos:\n{df.dtypes}")

        if df.empty:
            print(f"[leer_y_procesar_csv] DataFrame VACÍO en {ruta_archivo}. No se puede procesar.")
            return None

        #Ejemplo de uso de talib
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        print(f"[leer_y_procesar_csv] RSI calculado (primeras 5 filas):\n{df['RSI'].head().to_string()}")
        return df

    except FileNotFoundError: #Este error ya no debería ocurrir gracias a la comprobación anterior
        print(f"[leer_y_procesar_csv] ERROR: Archivo no encontrado en la ruta: {ruta_archivo}")
        return None
    except pd.errors.ParserError as e:
        print(f"[leer_y_procesar_csv] ERROR al leer el CSV: {e}")
        return None
    except KeyError as e:
        print(f"[leer_y_procesar_csv] ERROR de clave (posible problema con el índice o columnas): {e}")
        return None
    except Exception as e:
        print(f"[leer_y_procesar_csv] Ocurrió un error general: {e}")
        return None

def main():
    print("Iniciando el bot...")

    directorio_script_bot = os.path.dirname(os.path.abspath(__file__))
    nombre_archivo = "XBTUSDT_15m.csv"
    ruta_completa = os.path.join(directorio_script_bot, "datos_BTC", nombre_archivo)
    print(f"[main] Ruta completa al archivo: {ruta_completa}") #Mensaje dentro de main

    dataframe_procesado = leer_y_procesar_csv(ruta_completa)
    if dataframe_procesado is not None:
        print("[main] DataFrame procesado correctamente.")
        print("\n[main] Ejemplo de uso del DataFrame:")
        print(f"[main] Número de filas: {len(dataframe_procesado)}")
        if not dataframe_procesado.empty: #Añadido para evitar error si el DataFrame está vacio
            print(f"[main] Última fecha en los datos: {dataframe_procesado.index[-1]}")
            print(f"[main] Primer valor de 'close': {dataframe_procesado['close'][0]}")
            print(f"[main] Primer valor de RSI: {dataframe_procesado['RSI'][0]}")
    else:
        print("[main] No se pudo procesar el DataFrame. Deteniendo el bot.")
        return

    print("Bot en ejecución (simulado)...")
    while True:
        print("Bot haciendo cosas...")
        time.sleep(5)

if __name__ == "__main__":
    main()

import threading
import requests
import pandas as pd
import time
import datetime
import os
import talib

def obtener_ohlc_kraken(pair, interval, since=None):
    # Lógica para obtener datos desde Kraken
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

def leer_y_procesar_csv(ruta_archivo):
    """Lee un archivo CSV, lo imprime (opcional) y lo procesa."""
    try:
        print(f"[leer_y_procesar_csv] Intentando leer el archivo: {ruta_archivo}")
        if not os.path.exists(ruta_archivo): #Verifica si el archivo existe ANTES de intentar leerlo
            print(f"[leer_y_procesar_csv] ERROR: El archivo NO existe en la ruta: {ruta_archivo}")
            return None

        print(f"[leer_y_procesar_csv] Archivo EXISTE. Procediendo con la lectura...")
        df = pd.read_csv(ruta_archivo, index_col='time', parse_dates=True)

        #Ejemplo de uso de talib
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        print(f"[leer_y_procesar_csv] RSI calculado (primeras 5 filas):\n{df['RSI'].head().to_string()}")
        return df

    except FileNotFoundError: 
        print(f"[leer_y_procesar_csv] ERROR: Archivo no encontrado en la ruta: {ruta_archivo}")
        return None
    except Exception as e:
        print(f"[leer_y_procesar_csv] Ocurrió un error general: {e}")
        return None

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

def actualizar_dataframe(df, pair, interval):
    if df.empty:  # Si el DataFrame está vacío, obtener datos desde el inicio
        since = None
    else:
        last_timestamp = int(df.index[-1].timestamp()) + 1
        since = last_timestamp

    nuevos_datos = obtener_ohlc_kraken(pair, interval, since)

    if nuevos_datos is not None:
        if not nuevos_datos.empty: 
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')] 
            return df_actualizado
        else:
            print(f"No hay nuevos datos para el intervalo {interval}")
            return df
    else:
        print(f"Error al obtener nuevos datos para el intervalo {interval}")
        return df

# Función que se ejecutará en un hilo separado para procesar el CSV


def procesar_csv(pair, interval, carpeta="datos_BTC"):
    nombre_archivo = f"{pair}_{interval}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    dataframe_procesado = leer_y_procesar_csv(ruta_completa)
    if dataframe_procesado is not None:
        print(f"Archivo {nombre_archivo} procesado correctamente.")
    else:
        print(f"No se pudo procesar el archivo {nombre_archivo}.")

def main():
    print("Iniciando el bot...")
    directorio_script_bot = os.path.dirname(os.path.abspath(__file__))
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }

    while True:
        print("Actualizando datos...")
        for interval, filename_suffix in temporalidades.items():
            nombre_archivo = f"XBTUSDT_{filename_suffix}.csv"
            ruta_completa = os.path.join(directorio_script_bot, "datos_BTC", nombre_archivo)

            print(f"[main - DEBUG] Ruta completa: {ruta_completa}") #Imprime la ruta

            try:
                data = obtener_ohlc_kraken("XBT/USDT", interval)
                if data is not None:
                    guardar_dataframe(data, ruta_completa)
                    print(f"Datos guardados en {ruta_completa}")

                    # ***ESTE ES EL PUNTO CLAVE: LECTURA DESPUÉS DE GUARDAR***
                    if os.path.exists(ruta_completa): #Verifica si el archivo existe
                        print(f"[main - DEBUG] El archivo EXISTE.")
                        dataframe_procesado = leer_y_procesar_csv(ruta_completa)
                        if dataframe_procesado is not None:
                            print(f"[main] DataFrame de {nombre_archivo} procesado correctamente.")
                            # ***AQUÍ USAS EL DATAFRAME***
                            print(dataframe_procesado.tail().to_string()) #Imprime las ultimas lineas del dataframe
                            print(dataframe_procesado.dtypes) #Imprime los tipos de datos
                            #Ejemplo de uso de talib
                            dataframe_procesado['RSI'] = talib.RSI(dataframe_procesado['close'], timeperiod=14)
                            print(f"[main] RSI calculado (últimas 5 filas):\n{dataframe_procesado['RSI'].tail().to_string()}")
                        else:
                            print(f"[main] No se pudo procesar el DataFrame de {nombre_archivo}.")
                    else:
                        print(f"[main - ERROR] El archivo NO existe después de guardar.")

                else:
                    print(f"No se pudieron obtener datos para {interval}")

            except requests.exceptions.RequestException as e:
                print(f"Error en la solicitud a Kraken: {e}")
            except Exception as e:
                print(f"Ocurrió un error general: {e}")

        print("Datos actualizados. Esperando 60 segundos...")
        time.sleep(60)

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()

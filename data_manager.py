import requests
import pandas as pd
import os
import time
import talib
import datetime
import logging

# --- Funciones de la API de Kraken ---
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
            time.sleep(5)
    print("Número máximo de reintentos alcanzado.")
    return None

# --- Funciones de cálculo de indicadores ---
def calcular_rsi(df, period=14):
    df['RSI'] = talib.RSI(df['close'], timeperiod=period)
    return df

def calcular_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, macdsignal, macdhist = talib.MACD(df['close'], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    df['MACD'] = macd
    df['MACD_Signal'] = macdsignal
    df['MACD_Hist'] = macdhist
    return df

def calcular_bandas_bollinger(df, period=20, stddev=2):
    upper, middle, lower = talib.BBANDS(df['close'], timeperiod=period, nbdevup=stddev, nbdevdn=stddev)
    df['BB_Upper'] = upper
    df['BB_Middle'] = middle
    df['BB_Lower'] = lower
    return df

def calcular_hullma(df, period=9):
    df['HULLMA'] = talib.WMA(talib.WMA(df['close'], period//2).multiply(2).sub(talib.WMA(df['close'], period)), int(period**0.5))
    return df

def calcular_atr(df, period=14): # Función para calcular el ATR
    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=period)
    return df

def calcular_todos_indicadores(df):
    df = calcular_rsi(df)
    df = calcular_macd(df)
    df = calcular_bandas_bollinger(df)
    df = calcular_hullma(df)
    df = calcular_atr(df) # Llamada a la función para calcular el ATR
    return df

# --- Funciones de gestión de archivos CSV ---
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
    try:
        if not os.path.exists(ruta_archivo):
            print(f"[leer_y_procesar_csv] ERROR: El archivo NO existe en la ruta: {ruta_archivo}")
            return None

        df = pd.read_csv(ruta_archivo, index_col='time', parse_dates=True)
        print(f"[leer_y_procesar_csv] Datos leídos desde {ruta_archivo} (primeras 5 filas):\n{df.head().to_string()}")
        return df

    except FileNotFoundError:
        print(f"[leer_y_procesar_csv] ERROR: Archivo no encontrado en la ruta: {ruta_archivo}")
        return None
    except Exception as e:
        print(f"[leer_y_procesar_csv] Ocurrió un error general: {e}")
        return None

def actualizar_dataframe(df, pair, interval):
    if df.empty:
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

def actualizar_archivos(pair, carpeta="datos_BTC"):
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    os.makedirs(carpeta, exist_ok=True)
    for interval, filename_suffix in temporalidades.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        try:
            df = pd.read_csv(filename, index_col='time', parse_dates=True)
        except FileNotFoundError:
            logging.info(f"Archivo {filename} no encontrado. Creando archivo nuevo.")
            df = pd.DataFrame()

        df = actualizar_dataframe(df, pair, interval)

        if not df.empty:
            ahora_utc = pd.Timestamp.now(tz='UTC')  # Eliminada la línea innecesaria
            ultimo_timestamp_utc = df.index[-1]
            hora_cierre_esperada_utc = ultimo_timestamp_utc + pd.Timedelta(minutes=interval)

            # *** CORRECCIÓN IMPORTANTE: Localizar ahora_utc a UTC ***
            ahora_utc = ahora_utc.tz_localize('UTC')

            if hora_cierre_esperada_utc > ahora_utc:
                df = df[:-1]
                logging.info(f"Vela incompleta eliminada para {filename_suffix}")

            df = calcular_todos_indicadores(df)
        guardar_dataframe(df, filename)

# --- Función principal para ejecutar la actualización ---
def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"

    if not os.path.exists(carpeta_datos):
        os.makedirs(carpeta_datos)
        logging.info(f"Carpeta {carpeta_datos} creada.")

    while True:
        logging.info("Actualizando archivos...")
        actualizar_archivos(pair, carpeta_datos)

        logging.info("Datos actualizados. Esperando 30 segundos...")
        time.sleep(30)

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()

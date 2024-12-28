import threading
import requests
import pandas as pd
import time
import datetime
import os
import talib

# Función para obtener datos de Kraken
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

# Función para guardar el DataFrame
def guardar_dataframe(df, filename):
    if df is not None:
        try:
            df.to_csv(filename)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("No hay datos para guardar.")

# Función para agregar indicadores técnicos
def agregar_indicadores(df):
    try:
        # RSI
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)

        # Bandas de Bollinger
        upperband, middleband, lowerband = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BB_upper'] = upperband
        df['BB_middle'] = middleband
        df['BB_lower'] = lowerband

        # MACD
        macd, macdsignal, macdhist = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd
        df['MACD_signal'] = macdsignal
        df['MACD_hist'] = macdhist

        # Hull Moving Average (HMA)
        def hull_moving_average(series, period):
            half_length = period // 2
            sqrt_length = int(period**0.5)
            wma_half = talib.WMA(series, timeperiod=half_length)
            wma_full = talib.WMA(series, timeperiod=period)
            hull_ma = talib.WMA(2 * wma_half - wma_full, timeperiod=sqrt_length)
            return hull_ma

        df['HMA'] = hull_moving_average(df['close'], period=14)

        print("Indicadores calculados correctamente.")
    except Exception as e:
        print(f"Error al calcular indicadores: {e}")
    return df

# Función para actualizar archivos

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
        df = agregar_indicadores(df)
        guardar_dataframe(df, filename)

# Función para actualizar un DataFrame con nuevos datos
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

# Función para procesar archivos CSV
def procesar_csv(pair, interval, carpeta="datos_BTC"):
    nombre_archivo = f"{pair}_{interval}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    try:
        df = pd.read_csv(ruta_completa, index_col='time', parse_dates=True)
        df = agregar_indicadores(df)
        guardar_dataframe(df, ruta_completa)
        print(f"Archivo {nombre_archivo} procesado correctamente.")
    except Exception as e:
        print(f"Error al procesar el archivo {nombre_archivo}: {e}")

# Función principal
def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    os.makedirs(carpeta_datos, exist_ok=True)
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }

    while True:
        for interval, filename_suffix in temporalidades.items():
            print(f"Obteniendo datos para el intervalo de {filename_suffix}...")
            df = obtener_ohlc_kraken(pair, interval)
            if df is not None:
                filename = os.path.join(carpeta_datos, f"{pair}_{filename_suffix}.csv")
                df = agregar_indicadores(df)
                guardar_dataframe(df, filename)

                # Crear un hilo para procesar el CSV
                threading.Thread(target=procesar_csv, args=(pair, filename_suffix)).start()

        print("Datos actualizados. Esperando 60 segundos...")
        time.sleep(60)

if __name__ == "__main__":
    main()

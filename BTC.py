import requests
import pandas as pd
import time
import datetime
import os
import talib

# Funciones para obtener y guardar datos (se mantienen iguales)
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
            df = df.astype(float)  # Conversión explícita
            return df
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos de Kraken: {e}")
            time.sleep(5)
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

# Función para actualizar los datos
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

# Función para calcular y guardar indicadores
def calcular_y_guardar_indicadores(pair, carpeta="datos_BTC"):
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
            print(f"Procesando {filename}, longitud del dataframe: {len(df)}")
            df = calcular_indicadores(df)
            guardar_dataframe(df, filename)
        except FileNotFoundError:
            print(f"Archivo {filename} no encontrado. Se creará al actualizar los datos.")
        except Exception as e:
            print(f"Error procesando {filename}: {e}")

# Indicadores (se mantienen igual)
def calcular_indicadores(df):
    if len(df) >= 26:  # Verifica que haya suficientes datos
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        bbands = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = bbands
        macd = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = macd
    else:
        print("No hay datos suficientes para calcular los indicadores.")
    return df

# Bucle principal mejorado
def bucle_principal(pair, carpeta_datos, frecuencia_actualizacion):
    while True:
        try:
            print("Actualizando datos...")
            actualizar_archivos(pair, carpeta_datos)
            print("Calculando indicadores...")
            calcular_y_guardar_indicadores(pair, carpeta_datos)
            print(f"Esperando {frecuencia_actualizacion} segundos...")
            time.sleep(frecuencia_actualizacion)
        except KeyboardInterrupt:
            print("Bucle detenido por el usuario.")
            break
        except Exception as e:
            print(f"Error en el bucle principal: {e}")
            time.sleep(10)

# Ejecución
if __name__ == "__main__":
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    frecuencia_actualizacion = 60  # En segundos
    bucle_principal(pair, carpeta_datos, frecuencia_actualizacion)

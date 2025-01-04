
import requests
import pandas as pd
import os
import time
import talib
import logging

# Configuración del logging (más completa)
logging.basicConfig(filename='trading_bot.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# Constantes (para mejor mantenimiento)
API_URL = "https://api.kraken.com/0/public/OHLC"
RETRIES = 3
SLEEP_TIME = 30  # Segundos entre actualizaciones
PAIR = "XBTUSDT"
CARPETA_DATOS = "datos_BTC"
TEMPORALIDADES = {
    15: "15m",
    60: "1h",
    240: "4h",
    1440: "1d"
}

# --- Funciones de la API de Kraken ---
def obtener_ohlc_kraken(pair, interval, since=None):
    url = f"{API_URL}?pair={pair}&interval={interval}"
    if since:
        url += f"&since={since}"

    for i in range(RETRIES):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
            data = response.json()
            if data['error']:
                logging.error(f"Error de Kraken: {data['error']}")
                return None
            if not data['result']:
                logging.warning(f"No hay datos disponibles para {pair} en intervalo {interval}.")
                return None

            df = pd.DataFrame(data['result'][pair], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True) #inplace=True para modificar el dataframe original
            df = df.astype(float)
            return df
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener datos de Kraken (intento {i+1}): {e}")
            time.sleep(5)
    logging.error(f"Número máximo de reintentos ({RETRIES}) alcanzado para {pair} en intervalo {interval}.")
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


def calcular_hullma(df, period=12):

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
    if df is not None and not df.empty: #comprobar si el dataframe no esta vacio
        try:
            df.to_csv(filename)
            logging.info(f"Datos guardados en {filename}")
        except Exception as e:
            logging.error(f"Error al guardar el archivo {filename}: {e}")
    elif df.empty:
        logging.warning(f"No hay datos para guardar en {filename}. DataFrame vacío.")
    else:
        logging.warning("No hay datos para guardar. DataFrame es None.")


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
            logging.info(f"No hay nuevos datos para {pair} en el intervalo {interval}.")
            return df
    else:
        logging.error(f"Error al obtener nuevos datos para {pair} en el intervalo {interval}.")
        return df

def actualizar_archivos(pair=PAIR, carpeta=CARPETA_DATOS):
    os.makedirs(carpeta, exist_ok=True) #crear la carpeta si no existe antes de iterar
    for interval, filename_suffix in TEMPORALIDADES.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        try:
            df = pd.read_csv(filename, index_col='time', parse_dates=True)
            logging.info(f"Archivo {filename} leído correctamente.")
        except FileNotFoundError:
            logging.info(f"Archivo {filename} no encontrado. Creando archivo nuevo.")
            df = pd.DataFrame()
        except pd.errors.EmptyDataError: #Capturar el error si el archivo esta vacio
            logging.warning(f"Archivo {filename} esta vacio. Creando DataFrame vacio.")
            df = pd.DataFrame()
        except Exception as e:
            logging.error(f"Error al leer el archivo {filename}: {e}")
            continue

        df = actualizar_dataframe(df, pair, interval)

        if not df.empty:
            ahora = pd.Timestamp.now()
            ultimo_timestamp = df.index[-1]
            hora_cierre_esperada = ultimo_timestamp + pd.Timedelta(minutes=interval)

            if hora_cierre_esperada > ahora:
                df = df[:-1]
                logging.info(f"Vela incompleta eliminada para {filename_suffix}")

            df = calcular_todos_indicadores(df)
        guardar_dataframe(df, filename)
    logging.info("Archivos actualizados.")

def main():
    if not os.path.exists(CARPETA_DATOS):
        os.makedirs(CARPETA_DATOS)
        logging.info(f"Carpeta {CARPETA_DATOS} creada.")

    while True:
        logging.info("Actualizando archivos...")
        actualizar_archivos() # se llama a la funcion sin argumentos ya que estos estan definidos como constantes
        logging.info(f"Datos actualizados. Esperando {SLEEP_TIME} segundos...")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    main()

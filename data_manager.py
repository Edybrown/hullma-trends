import requests
import pandas as pd
import os
import time
import talib
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
                logging.error(f"Error de Kraken: {data['error']}")
                return None
            if not data['result']:
                logging.warning("No hay datos disponibles para este intervalo.")
                return None
            df = pd.DataFrame(data['result'][pair], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            df = df.astype(float)
            return df
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener datos de Kraken: {e}")
            time.sleep(5)
    logging.error("Número máximo de reintentos alcanzado.")
    return None

# --- Funciones de cálculo de indicadores ---
def calcular_todos_indicadores(df):
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    macd, macdsignal, macdhist = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = macd, macdsignal, macdhist
    upper, middle, lower = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = upper, middle, lower
    df['HULLMA'] = talib.WMA(talib.WMA(df['close'], 4.5).multiply(2).sub(talib.WMA(df['close'], 9)), 3)
    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    return df

# --- Funciones de gestión de archivos CSV ---
def guardar_dataframe(df, filename):
    try:
        df.to_csv(filename)
        logging.info(f"Datos guardados en {filename}")
    except Exception as e:
        logging.error(f"Error al guardar el archivo: {e}")

def actualizar_dataframe(df, pair, interval):
    if df.empty:
        since = None
    else:
        since = int(df.index[-1].timestamp()) + 1

    nuevos_datos = obtener_ohlc_kraken(pair, interval, since)

    if nuevos_datos is not None:
        if not nuevos_datos.empty:
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')]

            # Eliminar última vela si está incompleta
            ultimo_timestamp = df_actualizado.index[-1]
            hora_cierre_esperada = ultimo_timestamp + pd.Timedelta(minutes=interval)
            if hora_cierre_esperada > pd.Timestamp.now(tz='UTC'):
                logging.info(f"Eliminando última vela incompleta. Hora cierre esperada: {hora_cierre_esperada}")
                df_actualizado = df_actualizado[:-1]
            
            return df_actualizado
    else:
        logging.error(f"Error al obtener nuevos datos para el intervalo {interval}")
    
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
            df = calcular_todos_indicadores(df)
        
        guardar_dataframe(df, filename)

# --- Función principal ---
def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    os.makedirs(carpeta_datos, exist_ok=True)

    while True:
        logging.info("Actualizando archivos...")
        actualizar_archivos(pair, carpeta_datos)
        logging.info("Datos actualizados. Esperando 30 segundos...")
        time.sleep(30)

if __name__ == "__main__":
    main()

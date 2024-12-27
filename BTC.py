import requests
import pandas as pd
import time
import datetime

def obtener_ohlc_kraken(pair, since=None, interval=1):
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

# Ejemplo de uso:
pair = "XBTUSDT"  # Par BTC/USDT en Kraken (XBT es el símbolo de BTC en Kraken)
#Obtener datos desde una fecha especifica
desde = datetime.datetime(2023, 1, 1).timestamp()
df_ohlc_kraken = obtener_ohlc_kraken(pair, since=desde, interval=1440) #Intervalo de 1440 minutos = 1 dia

if df_ohlc_kraken is not None:
    print(df_ohlc_kraken.head())
    print(df_ohlc_kraken.tail())
else:
    print("No se pudieron obtener datos OHLC de Kraken.")

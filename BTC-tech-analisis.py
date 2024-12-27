import requests
import pandas as pd
import datetime

def obtener_precios_coingecko(coin_id, vs_currency, dias):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={vs_currency}&days={dias}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error en la petición a CoinGecko: {e}")
        return None

#Obtener datos OHLC de coingecko para un rango de fechas
def obtener_ohlc_coingecko(coin_id, vs_currency, desde, hasta):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency={vs_currency}&days=max"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df[desde:hasta]
        return df

    except requests.exceptions.RequestException as e:
        print(f"Error en la petición a CoinGecko: {e}")
        return None

#Ejemplo de uso de la funcion obtener_ohlc_coingecko
desde = datetime.datetime(2023, 1, 1)
hasta = datetime.datetime(2024, 1, 1)

df_ohlc = obtener_ohlc_coingecko("bitcoin", "usd", desde, hasta)

if df_ohlc is not None:
    print(df_ohlc.head())

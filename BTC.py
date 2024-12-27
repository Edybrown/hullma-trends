import requests
import pandas as pd
import datetime
import time

def obtener_ohlc_coingecko(coin_id, vs_currency, desde, hasta):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency={vs_currency}&days=max"
    retries = 3  # Número máximo de reintentos
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Lanza una excepción para códigos de error HTTP (incluido 401 si realmente ocurriera)
            data = response.json()
            if not data: # Verifica si la respuesta está vacía
                print("La respuesta de CoinGecko está vacía.")
                return None
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            df = df[desde:hasta]
            return df
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Código de error para Rate Limit
                retry_after = int(response.headers.get('Retry-After', 60))  # Obtener tiempo de espera o usar un valor predeterminado
                print(f"Rate limit alcanzado. Reintentando en {retry_after} segundos... (Intento {i+1}/{retries})")
                time.sleep(retry_after)
            else:
                print(f"Error en la petición a CoinGecko: {e}")
                return None
    print("Número máximo de reintentos alcanzado.")
    return None

# Ejemplo de uso:
desde = datetime.datetime(2023, 1, 1)
hasta = datetime.datetime(2024, 1, 1)

df_ohlc = obtener_ohlc_coingecko("bitcoin", "usd", desde, hasta)

if df_ohlc is not None:
    print(df_ohlc.head())
    print(df_ohlc.tail()) #Imprime la cola para verificar los datos mas recientes
else:
    print("No se pudieron obtener datos OHLC de CoinGecko.")

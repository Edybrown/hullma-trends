import requests

# Configura tu API Key aquí
API_KEY = "TU_API_KEY_AQUÍ"
BASE_URL = "https://api.coinalyze.net/v1"

# Función para obtener mercados spot
def obtener_mercados_spot():
    url = f"{BASE_URL}/spot-markets"
    headers = {"X-API-KEY": API_KEY}
    
    try:
        # Realiza la solicitud
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lanza un error si hay un problema con la respuesta
        mercados = response.json()
        
        # Filtra para encontrar BTC/USDT en Binance
        for mercado in mercados:
            if (
                mercado["exchange"].lower() == "binance" and
                mercado["base_asset"].lower() == "btc" and
                mercado["quote_asset"].lower() == "usdt"
            ):
                return mercado  # Devuelve el mercado encontrado
        return None  # Si no se encuentra, devuelve None
    
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener los mercados spot: {e}")
        return None

# Llamada principal
mercado_btc_usdt = obtener_mercados_spot()

# Verifica si se encontró el mercado y muestra los detalles
if mercado_btc_usdt:
    print("Mercado BTC/USDT en Binance encontrado:")
    print(f"  Símbolo: {mercado_btc_usdt['symbol']}")
    print(f"  Exchange: {mercado_btc_usdt['exchange']}")
    print(f"  Símbolo en Exchange: {mercado_btc_usdt['symbol_on_exchange']}")
    print(f"  Base Asset: {mercado_btc_usdt['base_asset']}")
    print(f"  Quote Asset: {mercado_btc_usdt['quote_asset']}")
else:
    print("No se encontró el mercado BTC/USDT en Binance.")

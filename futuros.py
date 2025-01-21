import requests

# Configura tu API Key aquí
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
BASE_URL = "https://api.coinalyze.net/v1"

# Función para obtener mercados spot
def obtener_mercados_spot():
    # La API Key se incluye directamente en la URL
    url = f"{BASE_URL}/spot-markets?apikey={API_KEY}"
    
    try:
        # Realiza la solicitud
        response = requests.get(url)
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

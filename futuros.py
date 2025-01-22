import requests
import json

# API Key
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

# URL base con la clave incluida
url = f"https://api.coinalyze.net/v1/spot-markets?api_key={api_key}"

def obtener_mercados_spot_btc(api_key):
    """
    Obtiene los mercados spot relacionados con BTC de la API de CoinAlyze.
    """
    try:
        # Solicitud a la API
        print("Realizando solicitud a la API...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza error si el código no es 200
        
        # Parsear los datos
        data = response.json()
        print(f"Total de mercados spot obtenidos: {len(data)}")
        
        # Filtrar solo los mercados que tienen BTC como base o como cotización
        mercados_spot_btc = [
            {
                "symbol": mercado["symbol"],
                "exchange": mercado["exchange"],
                "symbol_on_exchange": mercado["symbol_on_exchange"],
                "base_asset": mercado["base_asset"],
                "quote_asset": mercado["quote_asset"]
            }
            for mercado in data
            if mercado["base_asset"] == "BTC" or mercado["quote_asset"] == "BTC"
        ]
        
        print(f"Mercados spot relacionados con BTC encontrados: {len(mercados_spot_btc)}")
        
        # Guardar en un archivo
        with open("btc_spot_markets.txt", "w") as archivo:
            for mercado in mercados_spot_btc:
                archivo.write(json.dumps(mercado, indent=4) + "\n")
        
        print("Resultados guardados en 'btc_spot_markets.txt'")
    
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la solicitud: {e}")

# Ejecutar el script
if __name__ == "__main__":
    obtener_mercados_spot_btc(api_key)

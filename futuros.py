import requests
import json

# API Key
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

# URL base con la clave incluida
url = f"https://api.coinalyze.net/v1/future-markets?api_key={api_key}"

def obtener_perpetuos_btc(api_key):
    """
    Obtiene los mercados perpetuos de BTC de la API de CoinAlyze.
    """
    try:
        # Solicitud a la API
        print("Realizando solicitud a la API...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza error si el código no es 200
        
        # Parsear los datos
        data = response.json()
        print(f"Total de mercados obtenidos: {len(data)}")
        
        # Filtrar solo los mercados perpetuos de BTC
        perpetuos_btc = [
            {
                "symbol": mercado["symbol"],
                "exchange": mercado["exchange"],
                "symbol_on_exchange": mercado["symbol_on_exchange"],
                "base_asset": mercado["base_asset"],
                "quote_asset": mercado["quote_asset"],
                "margined": mercado["margined"]
            }
            for mercado in data
            if mercado["is_perpetual"] and mercado["base_asset"] == "BTC"
        ]
        
        print(f"Mercados perpetuos de BTC encontrados: {len(perpetuos_btc)}")
        
        # Guardar en un archivo
        with open("btc_perpetuos.txt", "w") as archivo:
            for mercado in perpetuos_btc:
                archivo.write(json.dumps(mercado, indent=4) + "\n")
        
        print("Resultados guardados en 'btc_perpetuos.txt'")
    
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la solicitud: {e}")

# Ejecutar el script
if __name__ == "__main__":
    obtener_perpetuos_btc(api_key)

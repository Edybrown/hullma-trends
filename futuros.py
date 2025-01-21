import requests
import json

# API Key
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

# URL base con la clave incluida
url = f"https://api.coinalyze.net/v1/spot-markets?api_key={api_key}"

def obtener_spot_btc(api_key):
    """
    Obtiene los mercados spot de BTC de la API de CoinAlyze.
    """
    try:
        # Solicitud a la API
        print("Realizando solicitud a la API...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza excepción para códigos de error HTTP (4xx o 5xx)

        # Parsear los datos
        data = response.json()
        print(f"Total de mercados obtenidos: {len(data)}")

        # Filtrar solo los mercados spot de BTC
        spot_btc = [
            {
                "symbol": mercado["symbol"],
                "exchange": mercado.get("exchange"), # Añadido para incluir el exchange
                "quote_asset": mercado.get("quote_asset"), # Añadido para incluir la moneda de cotización
            }
            for mercado in data
            if mercado.get("is_spot") and mercado.get("base_asset") == "BTC" # Usando .get() para evitar KeyError
        ]

        print(f"Mercados spot de BTC encontrados: {len(spot_btc)}")

        # Guardar en un archivo JSON (más adecuado para datos estructurados)
        with open("btc_spot.json", "w") as archivo:
            json.dump(spot_btc, archivo, indent=4) # Usa json.dump para guardar una lista de diccionarios

        print("Resultados guardados en 'btc_spot.json'")

    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la solicitud: {e}")
    except json.JSONDecodeError as e:
        print(f"Error al decodificar la respuesta JSON: {e}. Respuesta del servidor: {response.text if 'response' in locals() else 'No hay respuesta'}")
    except Exception as e:
      print(f"Ocurrió un error inesperado: {e}")

# Ejecutar el script
if __name__ == "__main__":
    obtener_spot_btc(api_key)

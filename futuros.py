import requests
import json

base_url = "https://api.coinalyze.net/v1"
endpoint = "/future-markets"
url = f"{base_url}{endpoint}"

try:
    response = requests.get(url)
    response.raise_for_status()  # Lanza una excepción para códigos de error HTTP

    data = response.json()

    if data:
        print("Mercados de Futuros Disponibles:")
        for market in data:
            print(f"- Símbolo: {market['symbol']}, Exchange: {market['exchange']}, Base: {market['baseAsset']}, Quote: {market['quoteAsset']}")
            # Puedes acceder a otros campos si son relevantes, como market['contractType']
    else:
        print("No se encontraron mercados de futuros.")

except requests.exceptions.RequestException as e:
    print(f"Error al obtener los mercados de futuros: {e}")
except json.JSONDecodeError as e:
    print(f"Error al decodificar JSON: {e}")

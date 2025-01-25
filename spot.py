import requests
import time
import json

API_KEY = "TU_API_KEY"  # Reemplaza con tu clave API real
SYMBOLS = "BTCUSDT.A"  # Símbolo correcto para perpetuos
INTERVAL = "1hour"
LIMIT = 1

# Calcula los timestamps 'from' y 'to' (ejemplo: última hora)
to_timestamp = int(time.time())
from_timestamp = to_timestamp - 3600  # Una hora atrás

ENDPOINT = "ohlcv-history"
BASE_URL = "https://api.coinalyze.net/v1/"

url = f"{BASE_URL}{ENDPOINT}?api_key={API_KEY}&symbols={SYMBOLS}&interval={INTERVAL}&from={from_timestamp}&to={to_timestamp}&limit={LIMIT}"

try:
    response = requests.get(url)
    response.raise_for_status()

    print(f"Conexión exitosa. Código de estado: {response.status_code}")

    data = response.json()

    if isinstance(data, dict) and "history" in data and isinstance(data["history"], list) and data["history"]:
        print("Ejemplo del primer registro:")
        print(json.dumps(data["history"][0], indent=4))
    elif isinstance(data, dict):
        print("Respuesta de la API:")
        print(json.dumps(data, indent=4))
    else:
        print("La respuesta no contiene datos history o no es un diccionario.")


except requests.exceptions.RequestException as e:
    print(f"Error en la solicitud: {e}")
    if 'response' in locals() and response is not None:
        print(f"Código de estado recibido: {response.status_code}")
        print(f"Texto de la respuesta: {response.text}")
except json.JSONDecodeError as e:
    print(f"Error al decodificar JSON: {e}")
    if 'response' in locals() and response is not None:
        print(f"Texto de la respuesta: {response.text}")
except Exception as e:
    print(f"Error inesperado: {e}")

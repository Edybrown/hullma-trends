import requests

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API key real
SYMBOL = "BTCUSDT.A"
ENDPOINT = "ohlcv-history"
BASE_URL = "https://api.coinalyze.net/v1/"

url = f"{BASE_URL}{ENDPOINT}?api_key={API_KEY}&symbol={SYMBOL}&limit=1" # Limitamos a 1 para una respuesta más rápida

try:
    response = requests.get(url)
    response.raise_for_status()  # Lanza una excepción si el código de estado no es 2xx

    print(f"Conexión exitosa. Código de estado: {response.status_code}")
    # Opcional: Imprimir una parte de la respuesta para verificar los datos
    data = response.json()
    if isinstance(data, dict) and "history" in data and isinstance(data["history"], list) and data["history"]:
        print("Ejemplo del primer registro (opcional):")
        print(data["history"][0])
    elif isinstance(data, dict):
        print("Respuesta de la API (opcional):")
        print(data)
    else:
        print("La respuesta no contiene datos history (opcional)")

except requests.exceptions.RequestException as e:
    print(f"Error en la solicitud: {e}")
    if 'response' in locals() and response is not None:
        print(f"Código de estado recibido: {response.status_code}")
        print(f"Texto de la respuesta: {response.text}") # Imprime el texto de la respuesta para depurar errores
except json.JSONDecodeError as e:
    print(f"Error al decodificar JSON: {e}")
    if 'response' in locals() and response is not None:
        print(f"Texto de la respuesta: {response.text}")
except Exception as e:
    print(f"Error inesperado: {e}")

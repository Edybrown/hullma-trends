import requests
import time

# Tu API Key de Coinanalyze
API_KEY = '78a5f138-1339-44b1-b209-554832b824f8'

# URL base de la API
BASE_URL = 'https://api.coinalyze.net/v1'

# Endpoint para obtener el historial del Funding Rate
endpoint = '/funding-rate-history'

# Parámetros necesarios para la solicitud
params = {
    'symbols': 'BTCUSDT_PERP',  # Un ejemplo de par de símbolos, puedes agregar más separados por coma
    'interval': '1hour',  # Intervalo deseado: "1min", "5min", "15min", "1hour", etc.
    'from': int(time.time()) - 86400,  # Hace 24 horas (timestamp UNIX)
    'to': int(time.time()),  # Ahora (timestamp UNIX)
    'api_key': API_KEY  # Clave API
}

# Realiza la solicitud GET a la API
def obtener_funding_rate():
    url = BASE_URL + endpoint
    try:
        # Realiza la solicitud GET con los parámetros
        response = requests.get(url, params=params)
        
        # Verifica el estado de la respuesta (200 OK)
        if response.status_code == 200:
            print("Comunicación exitosa!")
            print("Datos de Funding Rate:", response.json())
        else:
            print(f"Error en la comunicación. Código de estado: {response.status_code}")
            print("Detalles del error:", response.text)
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud: {err}")

# Ejecutar la función
obtener_funding_rate()


import requests
import time

# Tu API Key de Coinanalyze
API_KEY = '78a5f138-1339-44b1-b209-554832b824f8'

# URL base de la API
BASE_URL = 'https://api.coinalyze.net/v1'

# Endpoint para obtener el historial de funding rate
endpoint_funding_rate_history = '/funding-rate-history'

# Parámetros de consulta
symbols = 'BTCUSDT_PERP.A'  # Símbolo de ejemplo
interval = '1hour'  # Intervalo de ejemplo
to = int(time.time())  # Timestamp actual (en segundos)
from_timestamp = to - (24 * 60 * 60)  # Timestamp hace 24 horas (en segundos)

# Función para obtener datos del funding rate
def obtener_funding_rate_history():
    url = BASE_URL + endpoint_funding_rate_history
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    params = {
        'symbols': symbols,
        'interval': interval,
        'from': from_timestamp,
        'to': to
    }

    try:
        # Realiza la solicitud GET con los parámetros
        response = requests.get(url, headers=headers, params=params)
        
        # Verifica el estado de la respuesta (200 OK)
        if response.status_code == 200:
            print("Comunicación exitosa!")
            print("Respuesta de la API:", response.json())
        else:
            print(f"Error en la comunicación. Código de estado: {response.status_code}")
            print("Detalles del error:", response.text)
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud: {err}")

# Ejecutar la función
obtener_funding_rate_history()

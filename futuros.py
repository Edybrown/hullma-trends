import requests

# Tu API Key de Coinanalyze
API_KEY = '78a5f138-1339-44b1-b209-554832b824f8'

# URL base de la API
BASE_URL = 'https://api.coinalyze.net/v1'

# Endpoint para obtener el funding rate actual
endpoint_funding_rate = '/funding-rate-history'

# Función para probar la comunicación con la API
def prueba_comunicacion(endpoint):
    url = BASE_URL + endpoint
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    try:
        # Realiza la solicitud GET
        response = requests.get(url, headers=headers)
        
        # Verifica el estado de la respuesta (200 OK)
        if response.status_code == 200:
            print("Comunicación exitosa!")
            print("Respuesta de la API:", response.json())
        else:
            print(f"Error en la comunicación. Código de estado: {response.status_code}")
            print("Detalles del error:", response.text)
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud: {err}")

# Probar la comunicación
prueba_comunicacion(endpoint_funding_rate)

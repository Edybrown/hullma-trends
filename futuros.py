import requests
import json
import time
import datetime

# ***¡REEMPLAZA ESTO CON TU CLAVE API REAL!***
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

# URL base de la API
base_url = "https://api.coinalyze.net/v1"

def test_api_connection(use_header=True):
    """Prueba la conexión a la API de Coinanalyze usando /funding-rate-history."""
    endpoint = "/funding-rate-history"
    url = f"{base_url}{endpoint}"
    headers = {}
    params = {
        'symbols': 'BINANCE:BTCUSDT_PERP.A', #Símbolo necesario para este endpoint
        'interval': '1hour',
        'from': int(time.time()) - 3600, #Hace una hora
        'to': int(time.time())

    }

    if use_header:
        headers = {"Authorization": f"Bearer {api_key}"}
        print("\nProbando autenticación con Header:")
    else:
        params['api_key'] = api_key #Añade la api key a los params
        print("\nProbando autenticación con parámetro en la URL:")
    
    print(f"Clave API (para depuración): '{api_key}'") # ¡BORRAR DESPUÉS DE LA PRUEBA!
    print(f"URL de la solicitud: {url}")
    print(f"Headers: {headers}")
    print(f"Parámetros: {params}")

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        print("Conexión exitosa.")
        try:
            data = response.json()
            print("Respuesta (JSON):", json.dumps(data, indent=4))
        except json.JSONDecodeError:
            print("Respuesta (Texto):", response.text)

    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP: {http_err}")
        if http_err.response is not None:
          try:
            error_json = http_err.response.json()
            print(f"Detalles del error (JSON): {json.dumps(error_json, indent=4)}") # Intenta imprimir detalles en JSON
          except json.JSONDecodeError:
            print(f"Detalles del error (Texto): {http_err.response.text}") # Si no es JSON, imprime el texto
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud: {err}")

if __name__ == "__main__":
    # Prueba con autenticación en el header (recomendado)
    test_api_connection(use_header=True)
    # Prueba con autenticación en la URL (parámetro api_key)
    test_api_connection(use_header=False)

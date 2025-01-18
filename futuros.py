import requests
import json

# Tu API Key de Coinanalyze (¡REEMPLAZA CON TU CLAVE REAL!)
api_key = "78a5f138-1339-44b1-b209-554832b824f8"

# URL base de la API
base_url = "https://api.coinalyze.net/v1"

def test_api_connection():
    endpoint = "/ping"  # Endpoint para probar la conexión
    url = f"{base_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP

        if response.status_code == 200:
            print("Conexión exitosa a la API de Coinanalyze.")
            try:
                data = response.json()
                print("Respuesta de la API (JSON):")
                print(json.dumps(data, indent=4)) # Imprime el JSON formateado
            except json.JSONDecodeError:
                print("La respuesta de la API no está en formato JSON.")
                print("Respuesta de la API (Texto):", response.text)
        else:
            print(f"Error en la comunicación. Código de estado: {response.status_code}")
            print("Respuesta de la API (Texto):", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

if __name__ == "__main__":
    test_api_connection()

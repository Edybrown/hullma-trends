import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_future_markets(api_key):
    """
    Obtiene información sobre los mercados futuros de CoinAnalyze.

    Args:
        api_key (str): La clave API de CoinAnalyze.

    Returns:
        list: Una lista de diccionarios, cada uno representando un mercado futuro.
    """
    url = "https://api.coinalyze.net/v1/future-markets"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")  # Para inspeccionar el contenido
        response.raise_for_status()

        # Si no hay excepciones, procesa la respuesta JSON
        data = response.json()
        return data

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            print("Error de autenticación: Verifica tu clave API y los permisos.")
        else:
            print(f"HTTP error occurred: {http_err}")  # Error HTTP específico
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred: {req_err}")  # Error general de la solicitud
    except Exception as e:
        print(f"Unexpected error: {e}")  # Cualquier otro error inesperado
    return None

# Ejemplo de uso
if __name__ == "__main__":
    mercados = get_future_markets(api_key)
    if mercados:
        print(f"Se encontraron {len(mercados)} mercados futuros.")
    else:
        print("No se pudo obtener información sobre los mercados futuros.")

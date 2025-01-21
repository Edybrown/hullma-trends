import requests

api_key= "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_future_markets(api_key):
    """Obtiene información sobre los mercados futuros de CoinAnalyze.

    Args:
        api_key (str): La clave API de CoinAnalyze.

    Returns:
        list: Una lista de diccionarios, cada uno representando un mercado futuro.
    """

    url = "https://api.coinalyze.net/v1/future-markets"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lanza una excepción si la solicitud HTTP no fue exitosa

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error inesperado: Código de estado {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 401:
                print("Error de autenticación: Verifica tu clave API y los permisos.")
            else:
                print(f"Error de solicitud HTTP: {e}")
        else:
            print(f"Error de conexión: {e}")
        return None

# ... resto del código

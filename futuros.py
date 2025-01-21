import requests

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

        # Verificar el estado de la solicitud
        if response.status_code == 200:
            print("La conexión a la API fue exitosa.")
        else:
            print("Error en la solicitud. Código de estado:", response.status_code)

        # Si necesitas procesar los datos, puedes hacerlo aquí
        # data = response.json()
        # ...

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de la API: {e}")

if __name__ == "__main__":
    api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu clave API real
    get_future_markets(api_key)

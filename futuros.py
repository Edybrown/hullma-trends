import requests

def get_future_markets(api_key):
    """Obtiene información sobre los mercados futuros de CoinAnalyze.

    Args:
        api_key (str): La clave API de CoinAnalyze.

    Returns:
        list: Una lista de diccionarios, cada uno representando un mercado futuro.
    """

    url = "https://api.coinalyze.net/v1/future-markets"
    headers = {"Authorization": f"Bearer {6ecb2327-4d0c-49c8-9e96-2f5028891e1d}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for error HTTP status codes
        data = response.json()

        # Validar la estructura de los datos (opcional)
        for market in data.get('data', []):
            # Agregar aquí las validaciones necesarias, por ejemplo:
            assert 'symbol' in market, "Campo 'symbol' no encontrado"
            assert 'lastPrice' in market, "Campo 'lastPrice' no encontrado"

        return data['data']
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de la API: {e}")
        return []

if __name__ == "__main__":
    api_key = "tu_clave_api"  # Reemplaza con tu clave API
    markets = get_future_markets(api_key)

    for market in markets:
        print(f"Mercado: {market['symbol']}, Precio: {market['lastPrice']}, Volumen: {market['volume']}")

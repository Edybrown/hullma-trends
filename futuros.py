import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_btc_symbols(api_key):
    """
    Obtiene todos los símbolos de BTC en mercados de futuros.
    """
    url = f"https://api.coinalyze.net/v1/future-markets?api_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Verifica si la respuesta es válida (2xx)
        markets = response.json()

        # Filtra los mercados donde el base_asset es BTC
        btc_markets = [market for market in markets if market["base_asset"] == "BTC"]

        return btc_markets

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    btc_markets = get_btc_symbols(api_key)
    if btc_markets:
        print(f"Se encontraron {len(btc_markets)} mercados para BTC:")
        for market in btc_markets:
            print(f"- Símbolo: {market['symbol']}")
            print(f"  Exchange: {market['exchange']}")
            print(f"  Símbolo en Exchange: {market['symbol_on_exchange']}")
            print(f"  Es perpetuo: {market['is_perpetual']}")
            print(f"  Margen: {market['margined']}")
            print(f"  Expira en: {market.get('expire_at', 'N/A')}")
            print("-----")
    else:
        print("No se pudo obtener información sobre los mercados de BTC.")

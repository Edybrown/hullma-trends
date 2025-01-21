import requests

# Sustituye con tu propia API key
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
url = "https://api.coinalyze.net/v1/future-markets"

# Construir la URL con la API key
url_with_key = f"{url}?api_key={api_key}"

# Realizar la solicitud GET
response = requests.get(url_with_key)
markets = response.json()

# Filtrar el símbolo que deseas verificar
btc_perpetual_a = [market for market in markets if market.get("symbol") == "BTC-PERPETUAL.A"]

# Mostrar los resultados
print(btc_perpetual_a)

import requests

# URL de la API de CoinAlyze para mercados futuros
url = "https://api.coinalyze.net/v1/future-markets"

# Opcional: Agregar tu API Key si es necesario
headers = {
    "Authorization": "Bearer 6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
}

# Hacer la solicitud GET
response = requests.get(url, headers=headers)

# Verificar si la solicitud fue exitosa
if response.status_code == 200:
    # Convertir la respuesta a formato JSON
    data = response.json()

    # Mostrar algunos datos básicos (ajustar según la estructura de los datos)
    print("Datos de mercados futuros:")
    for market in data.get('data', []):
        print(f"Mercado: {market['symbol']}, Precio: {market['lastPrice']}, Volumen: {market['volume']}")
else:
    print(f"Error en la solicitud. Código de estado: {response.status_code}")

import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_supported_exchanges(api_key):
    """
    Obtiene la lista de intercambios soportados desde la API de Coinalyze.
    """
    url = "https://api.coinalyze.net/v1/exchanges"
    
    # Configura los encabezados con la clave API
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Lanza una excepción si el código de estado no es 2xx
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"Error al obtener los intercambios: {http_err}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    exchanges = get_supported_exchanges(api_key)
    if exchanges:
        for exchange in exchanges:
            print(f"Exchange: {exchange['name']} - Código: {exchange['code']}")
    else:
        print("No se pudo obtener la lista de intercambios.")

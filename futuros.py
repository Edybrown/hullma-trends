import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_future_markets(api_key):
    """
    Obtiene información sobre los mercados futuros usando la clave de API en la URL.
    """
    url = f"https://api.coinalyze.net/v1/future-markets?api_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza una excepción si el código de estado no es 2xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    mercados = get_future_markets(api_key)
    if mercados:
        print(f"Conexión exitosa. Se encontraron {len(mercados)} mercados futuros.")
    else:
        print("No se pudo obtener información sobre los mercados futuros.")

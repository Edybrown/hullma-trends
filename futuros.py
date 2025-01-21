import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_future_markets(api_key):
    """
    Intenta obtener información sobre los mercados futuros usando diferentes configuraciones de encabezados.
    """
    url = "https://api.coinalyze.net/v1/future-markets"

    # Prueba con "Bearer" en el encabezado
    headers1 = {"Authorization": f"Bearer {api_key}"}

    # Prueba con solo la clave API
    headers2 = {"Authorization": api_key}

    # Prueba con la clave en la URL
    url_with_key = f"{url}?api_key={api_key}"

    try:
        # Prueba 1
        print("Intentando con Bearer en el encabezado...")
        response = requests.get(url, headers=headers1, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        print(f"Error con Bearer: {http_err}")

    try:
        # Prueba 2
        print("Intentando con clave directa en el encabezado...")
        response = requests.get(url, headers=headers2, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        print(f"Error con clave directa: {http_err}")

    try:
        # Prueba 3
        print("Intentando con clave en la URL...")
        response = requests.get(url_with_key, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        print(f"Error con clave en la URL: {http_err}")

    return None

# Ejemplo de uso
if __name__ == "__main__":
    mercados = get_future_markets(api_key)
    if mercados:
        print(f"Se encontraron {len(mercados)} mercados futuros.")
    else:
        print("No se pudo obtener información sobre los mercados futuros.")

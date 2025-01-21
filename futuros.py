import requests

api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

def get_future_markets(api_key):
    """
    Prueba diferentes formas de conexión con la API de Coinalyze para identificar la correcta.
    """
    url = "https://api.coinalyze.net/v1/future-markets"

    # Configuraciones de prueba
    methods = {
        "Bearer Header": {"url": url, "headers": {"Authorization": f"Bearer {api_key}"}},
        "Direct API Key Header": {"url": url, "headers": {"Authorization": api_key}},
        "API Key in URL": {"url": f"{url}?api_key={api_key}", "headers": None}
    }

    for method_name, config in methods.items():
        print(f"Probando método: {method_name}")
        try:
            response = requests.get(config["url"], headers=config["headers"], timeout=10)
            print(f"HTTP Status Code ({method_name}): {response.status_code}")
            if response.status_code == 200:
                print(f"Respuesta válida con el método: {method_name}")
                return method_name, response.json()  # Devuelve el método exitoso y la respuesta
            else:
                print(f"Respuesta del servidor ({method_name}): {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error con el método {method_name}: {e}")

    return None, None

# Ejemplo de uso
if __name__ == "__main__":
    method_used, mercados = get_future_markets(api_key)
    if mercados:
        print(f"Se encontró conexión exitosa con el método: {method_used}")
        print(f"Se encontraron {len(mercados)} mercados futuros.")
    else:
        print("No se pudo obtener información sobre los mercados futuros.")

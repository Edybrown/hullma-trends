import requests
import time
import csv

# Tu API Key de Coinanalyze
api_key = "78a5f138-1339-44b1-b209-554832b824f8"

# Base URL para acceder a los datos de Coinanalyze
base_url = "https://api.coinalyze.net/v1/spot-markets"

# Función para realizar la solicitud con la clave en la URL
def get_data(endpoint, params=None):
    if params is None:
        params = {}
    params["api_key"] = api_key  # Añadir la API Key a los parámetros
    url = f"{base_url}{endpoint}"
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error en la solicitud a {url}: {response.status_code} {response.reason}")
        try:
            print("Detalles del error (JSON):", response.json())
        except json.JSONDecodeError:
            print("Respuesta del servidor no es JSON:", response.text)
        return None

# Función para guardar los datos en un archivo CSV
def save_to_csv(filename, data, header):
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)

# Ejemplo de uso 
if __name__ == "__main__":
  # Ejemplo para endpoint future-markets
  future_markets_data = get_data("/future-markets")

  if future_markets_data:
      print("Datos de futuros mercados obtenidos.")
  else:
      print("No se pudieron obtener datos de futuros mercados.")

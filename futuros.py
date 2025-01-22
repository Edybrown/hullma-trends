import requests

def get_open_interest_history(api_key, symbols, interval, from_timestamp, to_timestamp, convert_to_usd=False):
  """
  Obtiene el historial del interés abierto para los símbolos especificados.

  Args:
      api_key (str): Clave API de Coinanalyze.
      symbols (str): Símbolos separados por comas (máximo 20).
      interval (str): Intervalo/granularidad (ej. "1min", "5min", etc.).
      from_timestamp (int): Timestamp inicial (inclusivo) en segundos desde epoch.
      to_timestamp (int): Timestamp final (inclusivo) en segundos desde epoch.
      convert_to_usd (bool, optional): Convertir valores a USD (predeterminado: False).

  Returns:
      list: Lista de diccionarios con el historial del interés abierto para cada símbolo.
  """

  # Construir la URL con la API Key
  base_url = "https://api.coinalyze.net/v1/open-interest-history"
  params = {
      "api_key": api_key,
      "symbols": symbols,
      "interval": interval,
      "from": from_timestamp,
      "to": to_timestamp,
      "convert_to_usd": convert_to_usd,
  }
  url = f"{base_url}?{requests.compat.urlencode(params)}"

  # Realizar la solicitud
  try:
    response = requests.get(url)
    response.raise_for_status()  # Lanzar excepción para códigos de error HTTP (4xx o 5xx)
    return response.json()
  except requests.exceptions.RequestException as e:
    print(f"Error al realizar la solicitud: {e}")
    return None

# Ejemplo de uso
if __name__ == "__main__":
  # Reemplazar con tu API Key
  api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

  # Símbolos de ejemplo
  symbols = "BTCUSDT_PERP.A"

  # Intervalo de ejemplo
  interval = "1hour"

  # Timestamps de ejemplo (ajustar según tu necesidad)
  from_timestamp = int(time.time()) - (24 * 3600)  # Últimas 24 horas
  to_timestamp = int(time.time())

  # Convertir a USD (opcional)
  convert_to_usd = True

  # Realizar la solicitud
  data = get_open_interest_history(api_key, symbols, interval, from_timestamp, to_timestamp, convert_to_usd)

  if data:
    print("Historial del interés abierto obtenido:")
    for item in data:
      symbol = item["symbol"]
      history = item["history"]
      print(f"Símbolo: {symbol}")
      for entry in history:
        print(f"\t- Fecha: {entry['t']}")
        print(f"\t  Open: {entry['o']}")
        print(f"\t  High: {entry['h']}")
        print(f"\t  Low: {entry['l']}")
        print(f"\t  Close: {entry['c']}")
  else:
    print("Error al obtener el historial del interés abierto.")

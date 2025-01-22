import requests
import time
import json
from datetime import datetime, timedelta

def get_open_interest_history(api_key, symbols, interval, convert_to_usd=False, max_retries=3, retry_delay=5):
    """
    Obtiene el historial del interés abierto para los símbolos especificados.

    Args:
        api_key (str): Clave API de Coinanalyze.
        symbols (str): Símbolos separados por comas (máximo 20).
        interval (str): Intervalo/granularidad (ej. "1min", "5min", etc.).
        convert_to_usd (bool, optional): Convertir valores a USD (predeterminado: False).
        max_retries (int, optional): Número máximo de reintentos en caso de error.
        retry_delay (int, optional): Tiempo de espera entre reintentos en segundos.

    Returns:
        list: Lista de diccionarios con el historial del interés abierto para cada símbolo o None en caso de error.
    """
    base_url = "https://api.coinalyze.net/v1/open-interest-history"

    # Calcular el rango de tiempo máximo permitido según el intervalo
    if interval == "daily":
        max_data_points = float('inf')  # No hay límite para datos diarios
    else:
        max_data_points = 2000

    time_delta = get_time_delta_from_interval(interval)
    max_time_range = time_delta * max_data_points

    to_timestamp = int(time.time())
    from_timestamp = to_timestamp - max_time_range

    params = {
        "api_key": api_key,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": str(convert_to_usd).lower(),
    }

    url = f"{base_url}?{requests.compat.urlencode(params)}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10) # Timeout de 10 segundos
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            try:
                print(f"Respuesta del servidor: {response.text}")
            except:
                pass
            if attempt < max_retries - 1:
                time.sleep(retry_delay)  # Esperar antes de reintentar
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}. Respuesta: {response.text}")
            return None
    print(f"Fallo después de {max_retries} reintentos.")
    return None

def get_time_delta_from_interval(interval):
    """Convierte el string de intervalo a un delta de tiempo en segundos."""
    if interval == "1min": return 60
    elif interval == "5min": return 5 * 60
    elif interval == "15min": return 15 * 60
    elif interval == "30min": return 30 * 60
    elif interval == "1hour": return 60 * 60
    elif interval == "2hour": return 2 * 60 * 60
    elif interval == "4hour": return 4 * 60 * 60
    elif interval == "6hour": return 6 * 60 * 60
    elif interval == "12hour": return 12 * 60 * 60
    elif interval == "daily": return 24 * 60 * 60
    else:
        raise ValueError("Intervalo no válido")

if __name__ == "__main__":
    api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
    symbols = "BTCUSDT_PERP.A"
    interval = "1hour"
    convert_to_usd = True

    data = get_open_interest_history(api_key, symbols, interval, convert_to_usd)

    if data:
        print(json.dumps(data, indent=4)) # Imprime el JSON con formato
        # Ejemplo de como acceder a los datos:
        for item in data:
            print(f"Symbol: {item['symbol']}")
            for point in item.get('history', []): # Usar .get para evitar errores si no hay 'history'
                timestamp = point['t']
                readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {readable_time}: Open={point['o']}, High={point['h']}, Low={point['l']}, Close={point['c']}")
    else:
        print("No se pudieron obtener datos.")

import requests
import time
import csv
import datetime
import json

# Tu API Key de Coinanalyze (REEMPLAZA CON TU CLAVE REAL)
api_key = "TU_API_KEY"

# Base URL para acceder a los datos de Coinanalyze
base_url = "https://api.coinalyze.net/v1"

# Función para realizar la solicitud con autenticación y manejo de errores mejorado
def get_data(endpoint, params):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = f"{base_url}{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud a {url}: {e}")
        if response is not None:
          try:
            error_json = response.json()
            print(f"Detalles del error (JSON): {json.dumps(error_json, indent=4)}") # Intenta imprimir detalles en JSON
          except json.JSONDecodeError:
            print(f"Detalles del error (Texto): {response.text}") # Si no es JSON, imprime el texto
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return None



# Función para guardar los datos en un archivo CSV (sin cambios)
def save_to_csv(filename, data, header):
    if data is None:
        print(f"No hay datos para guardar en {filename}")
        return
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)
    print(f"Datos guardados correctamente en {filename}")

# Funciones para obtener datos (con manejo de errores y comprobación de 'data' en la respuesta)
def get_ohlcv_history(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/ohlcv-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    data = get_data(endpoint, params)
    return data['data'] if data and 'data' in data else None #Comprueba que exista 'data'

def get_funding_rate(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/funding-rate-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    data = get_data(endpoint, params)
    return data['data'] if data and 'data' in data else None

def get_liquidation_history(symbols, from_timestamp, to_timestamp):
    endpoint = "/liquidation-history"
    params = {
        "symbols": symbols,
        "from": from_timestamp,
        "to": to_timestamp
    }
    data = get_data(endpoint, params)
    return data['data'] if data and 'data' in data else None

def get_open_interest(symbols, interval, from_timestamp, to_timestamp): #Añadidos from y to
    endpoint = "/open-interest-history" #Endpoint correcto para historial
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    data = get_data(endpoint, params)
    return data['data'] if data and 'data' in data else None

def get_long_short_ratio(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/long-short-ratio-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    data = get_data(endpoint, params)
    return data['data'] if data and 'data' in data else None


# Ejemplo de uso (con comprobaciones y mejor manejo de fechas)
if __name__ == "__main__":
    symbols = "BINANCE:BTCUSDT_PERP"  # Símbolo con el exchange incluido
    interval = "1hour"
    dias_atras = 7 #Obtener los datos de los ultimos 7 dias
    to_timestamp = int(time.time())
    from_timestamp = to_timestamp - (dias_atras * 24 * 60 * 60)

    # Obtener y guardar datos (con comprobaciones de None)
    ohlcv_data = get_ohlcv_history(symbols, interval, from_timestamp, to_timestamp)
    save_to_csv("ohlcv_data.csv", ohlcv_data, ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])

    funding_rate_data = get_funding_rate(symbols, interval, from_timestamp, to_timestamp)
    save_to_csv("funding_rate_data.csv", funding_rate_data, ['timestamp', 'symbol', 'fundingRate'])

    liquidation_data = get_liquidation_history(symbols, from_timestamp, to_timestamp)
    save_to_csv("liquidation_history.csv", liquidation_data, ['timestamp', 'symbol', 'liquidationPrice'])

    open_interest_data = get_open_interest(symbols, interval, from_timestamp, to_timestamp)
    save_to_csv("open_interest_data.csv", open_interest_data, ['timestamp', 'symbol', 'openInterest'])

    long_short_ratio_data = get_long_short_ratio(symbols, interval, from_timestamp, to_timestamp)
    save_to_csv("long_short_ratio_data.csv", long_short_ratio_data, ['timestamp', 'symbol', 'longShortRatio'])

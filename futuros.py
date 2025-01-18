import requests
import time
import csv

# Tu API Key de Coinanalyze
api_key = "78a5f138-1339-44b1-b209-554832b824f8"

# Base URL para acceder a los datos de Coinanalyze
base_url = "https://api.coinalyze.net/v1"

# Función para realizar la solicitud con autenticación
def get_data(endpoint, params):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = f"{base_url}{endpoint}"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error en la comunicación. Código de estado: {response.status_code}")
        print("Detalles del error:", response.json())
        return None

# Función para guardar los datos en un archivo CSV
def save_to_csv(filename, data, header):
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)

# Función para obtener los datos OHLCV
def get_ohlcv_history(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/ohlcv-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    return get_data(endpoint, params)

# Función para obtener el historial de Funding Rate
def get_funding_rate(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/funding-rate-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    return get_data(endpoint, params)

# Función para obtener el historial de Liquidaciones
def get_liquidation_history(symbols, from_timestamp, to_timestamp):
    endpoint = "/liquidation-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    return get_data(endpoint, params)



# Función para obtener el Open Interest
def get_open_interest(symbols):
    endpoint = "/open-interest"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    return get_data(endpoint, params)

# Función para obtener el Long/Short Ratio
def get_long_short_ratio(symbols, interval, from_timestamp, to_timestamp):
    endpoint = "/long-short-ratio-history"
    params = {
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    return get_data(endpoint, params)

# Ejemplo de uso
if __name__ == "__main__":
    symbols = "BTCUSDT_PERP.A"  # Símbolos a utilizar
    interval = "1hour"        # Intervalo de tiempo (por ejemplo, "1hour", "5min", etc.)
    from_timestamp = int(time.time()) - (2000 * 3600)# 24 horas atrás
    to_timestamp = int(time.time())           # Hora actual

      # Obtener OHLCV History
    ohlcv_data = get_ohlcv_history(symbols, interval, from_timestamp, to_timestamp)
    if ohlcv_data:
        save_to_csv("ohlcv_data.csv", ohlcv_data['data'], ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
        print("Datos de OHLCV guardados.")

    
    # Obtener Funding Rate History
    funding_rate_data = get_funding_rate(symbols, interval, from_timestamp, to_timestamp)
    if funding_rate_data:
        save_to_csv("funding_rate_data.csv", funding_rate_data['data'], ['timestamp', 'symbol', 'fundingRate'])
        print("Datos de Funding Rate guardados.")

    # Obtener Liquidation History
    liquidation_history = get_liquidation_history(symbols, from_timestamp, to_timestamp)
    if liquidation_history:
        save_to_csv("liquidation_history.csv", liquidation_history['data'], ['timestamp', 'symbol', 'liquidationPrice'])
        print("Datos de Liquidation History guardados.")

  
    # Obtener Open Interest
    open_interest_data = get_open_interest(symbols)
    if open_interest_data:
        save_to_csv("open_interest_data.csv", open_interest_data['data'], ['timestamp', 'symbol', 'openInterest'])
        print("Datos de Open Interest guardados.")

    # Obtener Long/Short Ratio History
    long_short_ratio_data = get_long_short_ratio(symbols, interval, from_timestamp, to_timestamp)
    if long_short_ratio_data:
        save_to_csv("long_short_ratio_data.csv", long_short_ratio_data['data'], ['timestamp', 'symbol', 'longShortRatio'])
        print("Datos de Long/Short Ratio guardados.")

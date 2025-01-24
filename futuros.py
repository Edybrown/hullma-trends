import requests
import os
import pandas as pd
from datetime import datetime
import json
import time
import pytz

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "spot": "BTCUSDT.A",
    "perpetuos": "BTCUSDT_PERP.A"
}
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"

# Crear la carpeta de salida
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Fechas para obtener 2000 velas por temporalidad
VELAS = 2000
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

# Función para calcular el rango de timestamps
def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time()) # Usar time.time() para consistencia
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para hacer solicitudes a la API con manejo de errores mejorado y reintentos
def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp, convert_to_usd="false", max_retries=3):
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP erróneos (4xx o 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            try:
                print(f"Respuesta del servidor: {response.text}")
            except AttributeError: #Manejo por si response no existe
                pass
            if attempt < max_retries - 1:
                time.sleep(5)  # Esperar 5 segundos antes de reintentar
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}. Respuesta: {response.text}")
            return None
    print(f"Fallo después de {max_retries} reintentos para {url}.")
    return None

# Procesar cada tipo de dato (con manejo de múltiples símbolos)
def procesar_datos(temporalidad, velas_atras): # Añadimos velas_atras como argumento
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    all_data = {}

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp","o": "open","h": "high","l": "low","c": "close","v": "volume","bv": "buy_volume"}},
        "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp","o": "oi_open","h": "oi_high","l": "oi_low","c": "oi_close"}},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp","r": "long_short_ratio","l": "longs_percentage","s": "shorts_percentage"}},
        "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp","l": "liquidation_longs","s": "liquidation_shorts"}},
        "funding_rate": {"endpoint": "funding-rate-history", "renames": { "t": "timestamp", "o":"fr_open", "h":"fr_high", "l":"fr_low", "c":"fr_close" }} #Funding rate directamente de la API
    }

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} in {temporalidad}...")
        symbols_to_fetch = ",".join(SYMBOLS.values()) if data_type != "ohlcv" else SYMBOLS["perpetuos"]
        data = fetch_data(details["endpoint"], symbols_to_fetch, temporalidad, desde, hasta)

        if data and isinstance(data, dict) and "history" in data:
            history = data["history"]
            if isinstance(history, list):
                for item in history:
                    try:
                        timestamp = item["t"]
                        dt_utc = datetime.fromtimestamp(timestamp, tz=pytz.utc)
                        dt_local = dt_utc.astimezone(pytz.timezone('America/New_York'))
                        formatted_time = dt_local.strftime("%Y-%m-%d %H:%M:%S")

                        if formatted_time not in all_data: # Usar la fecha formateada directamente como clave
                            all_data[formatted_time] = {}

                        for key, new_key in details["renames"].items():
                            if key in item:
                                all_data[formatted_time][f"{data_type}_{new_key}_{SYMBOLS['perpetuos'] if data_type == 'funding_rate' else (SYMBOLS['perpetuos'] if data_type == 'ohlcv' else '')}"] = item[key]

                    except KeyError as e:
                        print(f"WARNING: Key {e} not found in data for {data_type} in {temporalidad}")
            else:
                print(f"WARNING: 'history' is not a list for {data_type} in {temporalidad}")
        elif data:
            print(f"WARNING: Data for {data_type} in {temporalidad} is not a dictionary or does not contain 'history'")
            print(data)
        else:
            print(f"WARNING: No data received for {data_type} in {temporalidad}")

    if all_data:
        df = pd.DataFrame.from_dict(all_data, orient='index')
        df.index.name = "fecha_hora" # Nombrar el índice
        df = df.sort_index()

        output_folder = os.path.join(OUTPUT_FOLDER, temporalidad)
        os.makedirs(output_folder, exist_ok=True)

        try:
            df.to_csv(os.path.join(output_folder, f"datos_{temporalidad}.csv"))
            print(f"Data saved to {output_folder}/datos_{temporalidad}.csv")
        except Exception as e: # Capturar cualquier excepción al guardar el archivo
            print(f"ERROR saving CSV: {e}")
            print(f"Directorio de trabajo: {os.getcwd()}") # Imprimir el directorio de trabajo actual para debug

    return None

# Guardar datos (sin velas_atras)
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    procesar_datos(temporalidad)

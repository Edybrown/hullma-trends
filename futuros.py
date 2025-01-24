import requests
import os
import pandas as pd
from datetime import datetime
import json
import time
import pytz

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOL_PERPETUOS = "BTCUSDT_PERP.A"  # Simplificado: solo perpetuos
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 1000
MAX_RETRIES = 5
RETRY_DELAY = 10
TIMEOUT = 30 # Timeout para las peticiones

# Crear la carpeta de salida
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

def fetch_data(endpoint, symbol, interval, from_timestamp, to_timestamp, convert_to_usd="false"):
    params = { # sin cambios
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}")

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()

            try: # INTENTO DE DECODIFICAR JSON Y VERIFICAR ESTRUCTURA
                data = response.json()
                if not isinstance(data, dict) or "history" not in data or not isinstance(data["history"], list):
                    print(f"WARNING: Estructura JSON inesperada: {data}") # Imprime la estructura para debug
                    return None # Retorna None si la estructura NO es correcta
                return data # Retorna los datos SOLO si la estructura es correcta
            except json.JSONDecodeError as e:
                print(f"Error al decodificar JSON: {e}. Texto de respuesta: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{MAX_RETRIES} fallido: {e}")
            if response is not None:
                print(f"Código de estado: {response.status_code}") # Imprime el código de estado HTTP
                print(f"Texto de respuesta: {response.text}") # Imprime el contenido de la respuesta para debug
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    print(f"Fallo después de {MAX_RETRIES} intentos para {url}")
    return None

def procesar_datos(temporalidad, data_types):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    output_folder = os.path.join(OUTPUT_FOLDER, temporalidad)
    os.makedirs(output_folder, exist_ok=True)

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} in {temporalidad}...")
        data = fetch_data(details["endpoint"], SYMBOL_PERPETUOS, temporalidad, desde, hasta) #symbol_perpetuos

        if not data or not isinstance(data, dict) or "history" not in data or not isinstance(data["history"], list):
            print(f"WARNING: Invalid data received for {data_type} in {temporalidad}. Skipping.")
            continue

        history = data["history"]
        all_data = {}

        for item in history:
            try:
                timestamp = item["t"]
                dt_utc = datetime.fromtimestamp(timestamp, tz=pytz.utc)
                dt_local = dt_utc.astimezone(pytz.timezone('America/New_York'))
                formatted_time = dt_local.strftime("%Y-%m-%d %H:%M:%S")

                all_data.setdefault(formatted_time, {})

                for key, new_key in details["renames"].items():
                    if key in item:
                        all_data[formatted_time][f"{data_type}_{new_key}"] = item[key] # Simplificado nombre de columna

            except KeyError as e:
                print(f"WARNING: Key {e} not found in data for {data_type} in {temporalidad}")

        if all_data:
            df = pd.DataFrame.from_dict(all_data, orient='index')
            df.index.name = "fecha_hora"
            df = df.sort_index()

            try:
                df.to_csv(os.path.join(output_folder, f"{data_type}_{temporalidad}.csv"))
                print(f"Data for {data_type} saved to {output_folder}/{data_type}_{temporalidad}.csv")
            except Exception as e:
                print(f"ERROR saving CSV for {data_type}: {e}")
                print(f"Directorio de trabajo: {os.getcwd()}")
        else:
            print(f"No data to save for {data_type} in {temporalidad}")

    return None

# Definición de data_types
data_types = {
    "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp","o": "open","h": "high","l": "low","c": "close","v": "volume","bv": "buy_volume"}},
    "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp","o": "oi_open","h": "oi_high","l": "oi_low","c": "oi_close"}},
    "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp","r": "long_short_ratio","l": "longs_percentage","s": "shorts_percentage"}},
    "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp","l": "liquidation_longs","s": "liquidation_shorts"}},
    "funding_rate": {"endpoint": "funding-rate-history", "renames": { "t": "timestamp", "o":"fr_open", "h":"fr_high", "l":"fr_low", "c":"fr_close" }}
}

# Bucle principal
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    procesar_datos(temporalidad, data_types)

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
SYMBOL_PERPETUOS = "BTCUSDT_PERP.A"
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000
MAX_RETRIES = 5
RETRY_DELAY = 10
TIMEOUT = 30

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
    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()

            try:
                data = response.json()
                if not isinstance(data, dict) or "history" not in data or not isinstance(data["history"], list):
                    print(f"WARNING: Estructura JSON inesperada para {endpoint} ({interval}): {data}")
                    return None
                return data
            except json.JSONDecodeError as e:
                print(f"Error al decodificar JSON para {endpoint} ({interval}): {e}. Respuesta: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{MAX_RETRIES} fallido para {endpoint} ({interval}): {e}")
            if response is not None:
                print(f"Código de estado: {response.status_code}")
                print(f"Texto de respuesta: {response.text}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    print(f"Fallo después de {MAX_RETRIES} intentos para {endpoint} ({interval})")
    return None


def procesar_datos(temporalidad, data_types):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    output_folder = os.path.join(OUTPUT_FOLDER, temporalidad)
    os.makedirs(output_folder, exist_ok=True)

    for data_type, details in data_types.items():
        data = fetch_data(details["endpoint"], SYMBOL_PERPETUOS, temporalidad, desde, hasta)

        if not data:
            print(f"WARNING: No data received for {data_type} in {temporalidad}. Skipping.")
            continue

        try:  # Intenta crear el DataFrame y guardar el CSV
            df = pd.DataFrame(data["history"])
            df["timestamp"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_convert('America/New_York')
            df.set_index("timestamp", inplace=True)
            df.rename(columns=details["renames"], inplace=True)
            df.to_csv(os.path.join(output_folder, f"{data_type}_{temporalidad}.csv"))
            print(f"Datos guardados para {data_type} en {temporalidad}")
        except (KeyError, ValueError, pd.errors.EmptyDataError) as e:
            print(f"Error al procesar/guardar datos para {data_type} en {temporalidad}: {e}")
            if data and "history" in data:
                print(f"Ejemplo de datos recibidos: {data['history'][:5]}") # Imprime los primeros 5 elementos de history
            elif data:
                print(f"Datos recibidos: {data}")
        except Exception as e:
            print(f"Error inesperado al procesar/guardar datos para {data_type} en {temporalidad}: {e}")


# Definición de data_types
data_types = {
    "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "bv": "buy_volume"}},
    "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp", "o": "oi_open", "h": "oi_high", "l": "oi_low", "c": "oi_close"}},
    "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp", "r": "long_short_ratio", "l": "longs_percentage", "s": "shorts_percentage"}},
    "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp", "l": "liquidation_longs", "s": "liquidation_shorts"}},
    "funding_rate": {"endpoint": "funding-rate-history", "renames": {"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close"}}
}

# Bucle principal
for temporalidad in TEMPORALIDADES:
    print(f"Procesando {temporalidad}...")
    procesar_datos(temporalidad, data_types)

print("Proceso completado.")

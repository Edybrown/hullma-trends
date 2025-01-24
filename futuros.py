import requests
import os
import pandas as pd
from datetime import datetime
import json
import time

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
    ahora = int(time.time())  # Usar time.time() para consistencia
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para hacer solicitudes a la API con manejo de errores y reintentos
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
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            time.sleep(5)
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            return None
    print(f"Fallo después de {max_retries} reintentos para {url}.")
    return None

# Procesar cada tipo de dato
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    all_data = {}

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "bv": "buy_volume"}},
        "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp", "o": "oi_open", "h": "oi_high", "l": "oi_low", "c": "oi_close"}},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp", "r": "long_short_ratio", "l": "longs_percentage", "s": "shorts_percentage"}},
        "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp", "l": "liquidation_longs", "s": "liquidation_shorts"}},
        "funding_rate": {"endpoint": "funding-rate-history", "renames": {"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close"}}
    }

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} for {temporalidad}...")
        symbols_to_fetch = ",".join(SYMBOLS.values()) if data_type != "ohlcv" else SYMBOLS["perpetuos"]
        data = fetch_data(details["endpoint"], symbols_to_fetch, temporalidad, desde, hasta)

        if data and isinstance(data, list):
            for item in data:
                timestamp = item.get("t")
                if timestamp:
                    dt_object = datetime.fromtimestamp(timestamp)
                    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
                    if timestamp not in all_data:
                        all_data[timestamp] = {"fecha_hora": formatted_time, "temporalidad": temporalidad}

                    for key, new_key in details["renames"].items():
                        if key in item:
                            all_data[timestamp][f"{data_type}_{new_key}"] = item[key]

    if all_data:
        final_df = pd.DataFrame.from_dict(all_data, orient='index')
        print("Preview de final_df:", final_df.head())
        print("Columnas disponibles:", final_df.columns)

        if "fecha_hora" not in final_df.columns:
            print("Error: La columna 'fecha_hora' no está en el DataFrame.")
            return

        final_df = final_df.sort_values(by="fecha_hora")
        file_path = os.path.join(OUTPUT_FOLDER, f"datos_{temporalidad}.csv")
        final_df.to_csv(file_path, index=False)
        print(f"Datos guardados en {file_path}")
    else:
        print(f"No se encontraron datos para la temporalidad: {temporalidad}")

# Guardar datos
for temporalidad in TEMPORALIDADES:
    print(f"Procesando temporalidad: {temporalidad}...")
    procesar_datos(temporalidad)

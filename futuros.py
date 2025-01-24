import requests
import os
import pandas as pd
from datetime import datetime
import time

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "spot": "BTCUSDT.A",
    "perpetuos": "BTCUSDT_PERP.A"
}
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"

# Crear carpeta de salida
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Fechas para obtener 2000 velas por temporalidad
VELAS = 2000
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

# Calcular rango de timestamps
def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para obtener datos
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
        except requests.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            time.sleep(5)
    return None

# Procesar datos y combinarlos con OHLCV
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    all_data = {}

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}},
        "funding_rate": {"endpoint": "funding-rate-history", "renames": {"o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close"}}
    }

    ohlcv_data = fetch_data(
        endpoint=data_types["ohlcv"]["endpoint"],
        symbols=SYMBOLS["perpetuos"],
        interval=temporalidad,
        from_timestamp=desde,
        to_timestamp=hasta
    )

    if not ohlcv_data or not isinstance(ohlcv_data, list):
        print(f"Error obteniendo datos OHLCV para {temporalidad}")
        return

    # Procesar OHLCV primero
    for item in ohlcv_data:
        timestamp = item.get("t")
        if not timestamp:
            continue
        dt_object = datetime.fromtimestamp(timestamp)
        formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
        all_data[timestamp] = {
            "fecha_hora": formatted_time,
            **{new_key: item.get(key, None) for key, new_key in data_types["ohlcv"]["renames"].items()}
        }

    # Procesar otros tipos de datos y unirlos
    for data_type, details in data_types.items():
        if data_type == "ohlcv":
            continue

        fetched_data = fetch_data(
            endpoint=details["endpoint"],
            symbols=",".join(SYMBOLS.values()),
            interval=temporalidad,
            from_timestamp=desde,
            to_timestamp=hasta
        )

        if not fetched_data or not isinstance(fetched_data, list):
            print(f"Error obteniendo datos {data_type} para {temporalidad}")
            continue

        for item in fetched_data:
            timestamp = item.get("t")
            if not timestamp or timestamp not in all_data:
                continue

            # Añadir datos al registro existente
            all_data[timestamp].update(
                {new_key: item.get(key, None) for key, new_key in details["renames"].items()}
            )

    # Crear DataFrame y guardar
    final_df = pd.DataFrame.from_dict(all_data, orient="index")
    final_df = final_df.sort_values(by="fecha_hora")
    final_df.to_csv(os.path.join(OUTPUT_FOLDER, f"datos_{temporalidad}.csv"), index=False)
    print(f"Datos guardados en {OUTPUT_FOLDER}/datos_{temporalidad}.csv")

# Ejecutar procesamiento
for temporalidad in TEMPORALIDADES:
    procesar_datos(temporalidad)

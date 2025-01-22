import requests
import os
import pandas as pd
from datetime import datetime

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "spot": "BTCUSDT.A",
    "perpetuos": "BTCUSDT_PERP.A"
}
TEMPORALIDADES = ["1hour", "4hour", "daily"]

# Fechas para obtener 2000 velas por temporalidad
VELAS = 2000
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

# Crear carpetas por temporalidad
for temp in TEMPORALIDADES:
    os.makedirs(temp, exist_ok=True)

# Función para calcular el rango de timestamps (sin cambios)
def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(datetime.now().timestamp())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para hacer solicitudes a la API (sin cambios)
def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp):
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Procesar cada tipo de dato (MODIFICADO)
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    dfs = []

    data_types = { #Definicion de los tipos de datos
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {
            "t": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
            "bv": "buy_volume"
        }},
        "open_interest": {"endpoint": "open-interest-history", "renames": {
            "t": "timestamp",
            "o": "oi_open",
            "h": "oi_high",
            "l": "oi_low",
            "c": "oi_close"
        }},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {
            "t": "timestamp",
            "r": "long_short_ratio",
            "l": "longs_percentage",
            "s": "shorts_percentage"
        }},
        "liquidation": {"endpoint": "liquidation-history", "renames": {
            "t": "timestamp",
            "l": "liquidation_longs",
            "s": "liquidation_shorts"
        }},
    }

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} in {temporalidad}...")
        symbols_to_fetch = ",".join(SYMBOLS.values()) if data_type != "ohlcv" else SYMBOLS["perpetuos"] #Manejo diferente para ohlcv
        data = fetch_data(details["endpoint"], symbols_to_fetch, temporalidad, desde, hasta)
        if data and "history" in data[0]:
            df = pd.DataFrame(data[0]["history"])
            df = df.rename(columns=details["renames"])
            df["data_type"] = data_type
            dfs.append(df)

    # Unificar DataFrames verticalmente
    if dfs:
        final_df = pd.concat(dfs, axis=0, ignore_index=True)
        final_df = final_df.sort_values(by="timestamp")
        final_df.to_csv(f"{temporalidad}/datos_unificados_{temporalidad}.csv", index=False) #Guardar el archivo aqui
        print(f"Data saved for {temporalidad}.")
        return None #Retornar None para que no intente guardar nuevamente en el bucle principal
    return None

# Guardar datos por temporalidad (MODIFICADO)
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    procesar_datos(temporalidad) #Llamar a la funcion que ahora guarda el archivo

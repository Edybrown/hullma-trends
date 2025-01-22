import requests
import os
import pandas as pd
from datetime import datetime
import json

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "spot": "BTCUSDT.A",
    "perpetuos": "BTCUSDT_PERP.A"
}
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"  # Carpeta de salida única

# Crear la carpeta de salida si no existe
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
    ahora = int(datetime.now().timestamp())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para hacer solicitudes a la API
def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp, convert_to_usd="false"):  #convert_to_usd añadido
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}") #Imprimir la URL completa para debug
    try:
        response = requests.get(url, params=params, timeout=10) # Timeout de 10 segundos
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        try:
            print(f"Respuesta del servidor: {response.text}")
        except:
            pass
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}. Respuesta: {response.text}")
        return None

# Procesar cada tipo de dato
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    all_data = []

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp","o": "open","h": "high","l": "low","c": "close","v": "volume","bv": "buy_volume"}},
        "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp","o": "oi_open","h": "oi_high","l": "oi_low","c": "oi_close"}},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp","r": "long_short_ratio","l": "longs_percentage","s": "shorts_percentage"}},
        "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp","l": "liquidation_longs","s": "liquidation_shorts"}},
    }

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} in {temporalidad}...")
        symbols_to_fetch = ",".join(SYMBOLS.values()) if data_type != "ohlcv" else SYMBOLS["perpetuos"]
        data = fetch_data(details["endpoint"], symbols_to_fetch, temporalidad, desde, hasta)

        if data and isinstance(data, list): #Comprobacion de que la respuesta sea una lista
            for symbol_data in data: #Iterar por cada symbolo devuelto
                if "history" in symbol_data and isinstance(symbol_data["history"], list) : #comprobacion de que history exista y sea una lista
                    for item in symbol_data["history"]:
                        row = {"timestamp": item["t"], "data_type": data_type, "temporalidad": temporalidad, "symbol":symbol_data["symbol"]}
                        for key, new_key in details["renames"].items():
                            if key in item:
                                row[new_key] = item[key]
                        all_data.append(row)

    if all_data:
        final_df = pd.DataFrame(all_data)
        final_df = final_df.sort_values(by="timestamp")
        final_df.to_csv(os.path.join(OUTPUT_FOLDER, f"datos_unificados.csv"), index=False) # Guardar en la carpeta única
        print(f"Data saved to {OUTPUT_FOLDER}/datos_unificados.csv")
        return None
    return None

# Guardar datos (modificado)
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    procesar_datos(temporalidad)

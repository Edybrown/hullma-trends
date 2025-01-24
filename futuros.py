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
OUTPUT_FOLDER = "datos_futuros"

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

# Función para hacer solicitudes a la API con manejo de errores mejorado y reintentos
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
            print(f"Respuesta exitosa para {endpoint} en el intento {attempt + 1}: {response.text}")  # Agregar log de respuesta exitosa
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            try:
                print(f"Respuesta del servidor (si existe): {response.text}")  # Mostrar respuesta incluso si hay error
            except AttributeError:  # Manejo por si response no existe
                pass
            if attempt < max_retries - 1:
                time.sleep(5)  # Esperar 5 segundos antes de reintentar
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}. Respuesta: {response.text}")
            return None
    print(f"Fallo después de {max_retries} reintentos para {url}.")
    return None


# Procesar cada tipo de dato (con manejo de múltiples símbolos)
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    all_data = {}

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "bv": "buy_volume"}},
        "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp", "o": "oi_open", "h": "oi_high", "l": "oi_low", "c": "oi_close"}},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp", "r": "long_short_ratio", "l": "longs_percentage", "s": "shorts_percentage"}},
        "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp", "l": "liquidation_longs", "s": "liquidation_shorts"}},
        "funding_rate": {"endpoint": "funding-rate-history", "renames": {"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close"}}  # Funding rate directamente de la API
    }

    # Solo necesitamos los datos de OHLCV para alinear las fechas
    ohlcv_data = fetch_data(data_types["ohlcv"]["endpoint"], SYMBOLS["perpetuos"], temporalidad, desde, hasta)
    
    if ohlcv_data and isinstance(ohlcv_data, dict) and "history" in ohlcv_data:
        for item in ohlcv_data["history"]:
            try:
                timestamp = item["t"]
                formatted_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                all_data[timestamp] = {"fecha_hora": formatted_time, "temporalidad": temporalidad}
            except KeyError as e:
                print(f"Error al acceder al timestamp en item: {item}. Error: {e}")

    # Procesar los otros datos con el mismo timestamp
    for data_type, details in data_types.items():
        if data_type == "ohlcv":  # Ya lo hemos procesado
            continue
        
        print(f"Fetching {data_type} in {temporalidad}...")
        symbols_to_fetch = ",".join(SYMBOLS.values()) if data_type != "ohlcv" else SYMBOLS["perpetuos"]
        data = fetch_data(details["endpoint"], symbols_to_fetch, temporalidad, desde, hasta)

        if data and isinstance(data, dict) and "history" in data:
            for item in data["history"]:
                try:
                    timestamp = item["t"]
                    if timestamp in all_data:  # Solo añadir si ya tenemos el timestamp en los datos de ohlcv
                        for key, new_key in details["renames"].items():
                            if key in item:
                                all_data[timestamp][new_key] = item[key]
                except KeyError as e:
                    print(f"Error al acceder al timestamp en item: {item}. Error: {e}")

    # Crear el DataFrame con los datos recopilados
    if all_data:
        final_df = pd.DataFrame.from_dict(all_data, orient='index')
        final_df = final_df.sort_values(by="fecha_hora")
        
        # Verificación de datos antes de guardar
        print(f"Datos procesados para {temporalidad}:")
        print(final_df.head())  # Mostrar las primeras filas para verificar

        if not final_df.empty:
            # Guardar en archivo CSV con nombre adecuado
            csv_filename = os.path.join(OUTPUT_FOLDER, f"datos_{temporalidad}.csv")
            final_df.to_csv(csv_filename, index=False)
            print(f"Data saved to {csv_filename}")
        else:
            print(f"No hay datos para guardar en {temporalidad}.")
    else:
        print(f"No se procesaron datos para {temporalidad}.")
    
# Guardar datos para cada temporalidad
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    procesar_datos(temporalidad)

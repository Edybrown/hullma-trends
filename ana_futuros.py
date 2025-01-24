import requests
import os
import pandas as pd
from datetime import datetime
import json
import time
import requests.compat

# Parámetros generales
API_KEY = "import requests
import os
import pandas as pd
from datetime import datetime
import json
import time
import requests.compat

# Parámetros generales
API_KEY = "TU_API_KEY"  # ¡REEMPLAZA CON TU API KEY REAL!
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {"perpetuos": "BTCUSDT_PERP.A"}  # Puedes agregar más símbolos aquí
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000  # Número de velas a obtener
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp, max_retries=3):
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}") # Imprime la URL completa
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP no exitosos (4xx o 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # Espera antes de reintentar
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}. Respuesta: {response.text if 'response' in locals() else 'No hay respuesta'}")
            return None
    print(f"Fallo después de {max_retries} reintentos para {url}.")
    return None

def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

def obtener_funding_rate(temporalidad, desde, hasta):
    endpoint = "funding-rate-history"
    symbol = SYMBOLS["perpetuos"]
    data = fetch_data(endpoint, symbol, temporalidad, desde, hasta)
    return data

def agregar_funding_rate_a_csv(temporalidad, desde, hasta):
    nombre_archivo = f"datos_{temporalidad}.csv"
    ruta_archivo = os.path.join(OUTPUT_FOLDER, nombre_archivo)
    print(f"Procesando archivo: {nombre_archivo}")

    try:
        df = pd.read_csv(ruta_archivo)
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {nombre_archivo}. Asegúrate de que exista.")
        return

    funding_rate_data = obtener_funding_rate(temporalidad, desde, hasta)

    if funding_rate_data and isinstance(funding_rate_data, list):
        all_funding_data = []
        for symbol_data in funding_rate_data:
            history = symbol_data.get("history")
            if history:
                for item in history:
                    item["symbol"] = symbol_data.get("symbol")
                    all_funding_data.append(item)
            else:
                symbol_data["symbol"] = symbol_data.get("symbol")
                all_funding_data.append(symbol_data)

        funding_rate_df = pd.DataFrame(all_funding_data)
        if not funding_rate_df.empty:
            funding_rate_df = funding_rate_df.rename(columns={"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close", "f":"funding_rate"})
            funding_rate_df['fecha_hora'] = pd.to_datetime(funding_rate_df['timestamp'], unit='s')
            columnas_merge = ['fecha_hora', 'fr_open', 'fr_high', 'fr_low', 'fr_close','funding_rate','symbol']
            df = pd.merge(df, funding_rate_df[columnas_merge], on='fecha_hora', how='left')
            df.to_csv(ruta_archivo, index=False)
            print(f"Funding rate agregado a {nombre_archivo}")
        else:
            print(f"No hay datos de funding rate para {temporalidad} en el rango especificado.")
    elif funding_rate_data is None:
        print(f"Error al obtener funding rate para {temporalidad}. La API devolvió None. Revisa la URL y la conexión.")
    else:
        print(f"Error al obtener funding rate para {temporalidad}. Tipo de dato inesperado: {type(funding_rate_data)}")
    print(f"Finalizado el procesamiento de {nombre_archivo}")

# Crear la carpeta de salida si no existe
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"Carpeta '{OUTPUT_FOLDER}' creada.")

print("Iniciando el script...")

# Procesar cada temporalidad
for temporalidad in TEMPORALIDADES:
    print(f"Procesando {temporalidad}...")
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    agregar_funding_rate_a_csv(temporalidad, desde, hasta)

print("Proceso completado.")"  # ¡REEMPLAZA CON TU API KEY REAL!
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {"perpetuos": "BTCUSDT_PERP.A"}  # Puedes agregar más símbolos aquí
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000  # Número de velas a obtener
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp, max_retries=3):
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}") # Imprime la URL completa
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP no exitosos (4xx o 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # Espera antes de reintentar
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}. Respuesta: {response.text if 'response' in locals() else 'No hay respuesta'}")
            return None
    print(f"Fallo después de {max_retries} reintentos para {url}.")
    return None

def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

def obtener_funding_rate(temporalidad, desde, hasta):
    endpoint = "funding-rate-history"
    symbol = SYMBOLS["perpetuos"]
    data = fetch_data(endpoint, symbol, temporalidad, desde, hasta)
    return data

def agregar_funding_rate_a_csv(temporalidad, desde, hasta):
    nombre_archivo = f"datos_{temporalidad}.csv"
    ruta_archivo = os.path.join(OUTPUT_FOLDER, nombre_archivo)
    print(f"Procesando archivo: {nombre_archivo}")

    try:
        df = pd.read_csv(ruta_archivo)
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {nombre_archivo}. Asegúrate de que exista.")
        return

    funding_rate_data = obtener_funding_rate(temporalidad, desde, hasta)

    if funding_rate_data and isinstance(funding_rate_data, list):
        all_funding_data = []
        for symbol_data in funding_rate_data:
            history = symbol_data.get("history")
            if history:
                for item in history:
                    item["symbol"] = symbol_data.get("symbol")
                    all_funding_data.append(item)
            else:
                symbol_data["symbol"] = symbol_data.get("symbol")
                all_funding_data.append(symbol_data)

        funding_rate_df = pd.DataFrame(all_funding_data)
        if not funding_rate_df.empty:
            funding_rate_df = funding_rate_df.rename(columns={"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close", "f":"funding_rate"})
            funding_rate_df['fecha_hora'] = pd.to_datetime(funding_rate_df['timestamp'], unit='s')
            columnas_merge = ['fecha_hora', 'fr_open', 'fr_high', 'fr_low', 'fr_close','funding_rate','symbol']
            df = pd.merge(df, funding_rate_df[columnas_merge], on='fecha_hora', how='left')
            df.to_csv(ruta_archivo, index=False)
            print(f"Funding rate agregado a {nombre_archivo}")
        else:
            print(f"No hay datos de funding rate para {temporalidad} en el rango especificado.")
    elif funding_rate_data is None:
        print(f"Error al obtener funding rate para {temporalidad}. La API devolvió None. Revisa la URL y la conexión.")
    else:
        print(f"Error al obtener funding rate para {temporalidad}. Tipo de dato inesperado: {type(funding_rate_data)}")
    print(f"Finalizado el procesamiento de {nombre_archivo}")

# Crear la carpeta de salida si no existe
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"Carpeta '{OUTPUT_FOLDER}' creada.")

print("Iniciando el script...")

# Procesar cada temporalidad
for temporalidad in TEMPORALIDADES:
    print(f"Procesando {temporalidad}...")
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    agregar_funding_rate_a_csv(temporalidad, desde, hasta)

print("Proceso completado.")

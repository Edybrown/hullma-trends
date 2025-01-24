import requests
import os
import pandas as pd
from datetime import datetime
import json
import time

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {"perpetuos": "BTCUSDT_PERP.A"}
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000
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
    print(f"URL: {url}?{requests.compat.urlencode(params)}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{max_retries} fallido: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
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

    try:
        df = pd.read_csv(ruta_archivo)
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {nombre_archivo}")
        return

    funding_rate_data = obtener_funding_rate(temporalidad, desde, hasta)

    if funding_rate_data:
        # Check if 'funding_rate' column exists in funding_rate_df
        if 'funding_rate' in funding_rate_df.columns:
            df = pd.merge(df, funding_rate_df[['fecha_hora', 'fr_open', 'fr_high', 'fr_low', 'fr_close', 'funding_rate']], on='fecha_hora', how='left')
        else:
            # Handle case where 'funding_rate' might be missing (optional)
            print("Warning: 'funding_rate' column not found in funding_rate_df. Skipping merge.")

        df.to_csv(ruta_archivo, index=False)
        print(f"Funding rate agregado a {nombre_archivo}")
    else:
        print(f"Error al obtener funding rate para {temporalidad}")

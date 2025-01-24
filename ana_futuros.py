import requests
import os
import pandas as pd
from datetime import datetime
import json
import time

# Parámetros generales (sin cambios)
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key real
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "perpetuos": "BTCUSDT_PERP.A"
}
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000
TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

# ... (Función fetch_data anterior, sin cambios)

def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time()) # Usar time.time() para consistencia
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

def obtener_funding_rate(temporalidad, desde, hasta):
    endpoint = "funding-rate-history"
    symbol = SYMBOLS["perpetuos"]
    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": temporalidad,
        "from": desde,
        "to": hasta
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL Funding Rate: {url}?{requests.compat.urlencode(params)}")
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
        for symbol_data in funding_rate_data: #Iteramos por symbolos
            history = symbol_data.get("history") #Obtenemos el history si existe
            if history:
                funding_rate_data= history #asignamos history si existe
            else:
                funding_rate_data = [symbol_data] #creamos una lista con el objeto actual, para que funcione el resto del codigo
            funding_rate_df = pd.DataFrame(funding_rate_data)
            if not funding_rate_df.empty: # Verificamos si el dataframe tiene datos
                funding_rate_df = funding_rate_df.rename(columns={"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close", "f":"funding_rate"})
                funding_rate_df['timestamp'] = pd.to_datetime(funding_rate_df['timestamp'], unit='s')
                funding_rate_df = funding_rate_df.rename(columns={"timestamp": "fecha_hora"})
                df = pd.merge(df, funding_rate_df[['fecha_hora', 'fr_open', 'fr_high', 'fr_low', 'fr_close','funding_rate']], on='fecha_hora', how='left')
                df.to_csv(ruta_archivo, index=False)
                print(f"Funding rate agregado a {nombre_archivo}")
            else:
                print(f"No hay datos de funding rate para {temporalidad} en el rango especificado")

    else:
        print(f"Error al obtener funding rate para {temporalidad}")

# Procesar cada temporalidad (sin cambios)
for temporalidad in TEMPORALIDADES:
    print(f"Procesando {temporalidad}...")
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    agregar_funding_rate_a_csv(temporalidad, desde, hasta)

print("Proceso completado.")

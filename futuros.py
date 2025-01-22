import requests
import os
import pandas as pd
from datetime import datetime

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
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

# Función para calcular el rango de timestamps
def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(datetime.now().timestamp())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para hacer solicitudes a la API
def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp):
    url = f"{BASE_URL}{endpoint}?symbols={symbols}&interval={interval}&from={from_timestamp}&to={to_timestamp}&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Procesar cada tipo de dato
def procesar_datos(temporalidad):
    desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
    dfs = []

    # OHLCV
    for market, symbol in SYMBOLS.items():
        print(f"Fetching OHLCV for {market} ({symbol}) in {temporalidad}...")
        data = fetch_data("ohlcv-history", symbol, temporalidad, desde, hasta)
        if data and "history" in data[0]:
            df = pd.DataFrame(data[0]["history"])
            df = df.rename(columns={
                "t": "timestamp",
                "o": f"ohlcv_open_{market}",
                "h": f"ohlcv_high_{market}",
                "l": f"ohlcv_low_{market}",
                "c": f"ohlcv_close_{market}",
                "v": f"ohlcv_volume_{market}",
                "bv": f"ohlcv_buy_volume_{market}"
            })
            dfs.append(df)

    # Open Interest
    print(f"Fetching Open Interest in {temporalidad}...")
    symbols = ",".join(SYMBOLS.values())
    data = fetch_data("open-interest-history", symbols, temporalidad, desde, hasta)
    if data and "history" in data[0]:
        df = pd.DataFrame(data[0]["history"])
        df = df.rename(columns={
            "t": "timestamp",
            "o": "oi_open",
            "h": "oi_high",
            "l": "oi_low",
            "c": "oi_close"
        })
        dfs.append(df)

    # Long/Short Ratio
    print(f"Fetching Long/Short Ratio in {temporalidad}...")
    data = fetch_data("long-short-ratio-history", symbols, temporalidad, desde, hasta)
    if data and "history" in data[0]:
        df = pd.DataFrame(data[0]["history"])
        df = df.rename(columns={
            "t": "timestamp",
            "r": "long_short_ratio",
            "l": "longs_percentage",
            "s": "shorts_percentage"
        })
        dfs.append(df)

    # Liquidation History
    print(f"Fetching Liquidation History in {temporalidad}...")
    data = fetch_data("liquidation-history", symbols, temporalidad, desde, hasta)
    if data and "history" in data[0]:
        df = pd.DataFrame(data[0]["history"])
        df = df.rename(columns={
            "t": "timestamp",
            "l": "liquidation_longs",
            "s": "liquidation_shorts"
        })
        dfs.append(df)

    # Unificar todos los DataFrames por timestamp
    if dfs:
        final_df = pd.concat(dfs, axis=1).loc[:, ~pd.concat(dfs, axis=1).columns.duplicated()]
        final_df = final_df.sort_values(by="timestamp")
        return final_df
    return None

# Guardar datos por temporalidad
for temporalidad in TEMPORALIDADES:
    print(f"Processing {temporalidad}...")
    final_data = procesar_datos(temporalidad)
    if final_data is not None:
        final_data.to_csv(f"{temporalidad}/datos_unificados_{temporalidad}.csv", index=False)
        print(f"Data saved for {temporalidad}.")
    else:
        print(f"No data for {temporalidad}.")

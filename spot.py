import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la API
BASE_URL = "https://api.coinalyze.net/v1/ohlcv-history"
SYMBOL = "BTCUSDT.A"  # Par para spot en Coinalyze
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu clave API si es necesario

# Función para obtener datos de OHLCV
def get_ohlcv(symbol, interval, num_candles):
    # Calcular timestamps (retrocedemos el tiempo necesario para obtener 2000 velas)
    end_time = int(datetime.now().timestamp())  # Ahora
    start_time = end_time - num_candles * interval_to_seconds(interval)  # Inicio

    # Parámetros para la API
    params = {
        "symbols": symbol,
        "interval": interval,
        "from": start_time,
        "to": end_time
    }

    # Solicitar datos a la API
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        ohlcv_data = data[0]["history"]  # Datos OHLCV
        return pd.DataFrame(ohlcv_data)
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Función para convertir intervalos a segundos
def interval_to_seconds(interval):
    intervals = {
        "1hour": 3600,
        "4hour": 14400,
        "daily": 86400
    }
    return intervals.get(interval, 0)

# Procesar datos para cada temporalidad
def process_intervals():
    intervals = ["1hour", "4hour", "daily"]
    writer = pd.ExcelWriter("BTCUSDT_OHLCV.xlsx", engine="xlsxwriter")  # Crear archivo Excel

    for interval in intervals:
        print(f"Obteniendo datos para {interval}...")
        df = get_ohlcv(SYMBOL, interval, 2000)  # Obtener 2000 velas
        if df is not None:
            # Convertir timestamp y renombrar columnas
            df["t"] = pd.to_datetime(df["t"], unit="s")
            df.rename(columns={
                "t": "Time",
                "o": "Open",
                "h": "High",
                "l": "Low",
                "c": "Close",
                "v": "Volume",
                "bv": "Buy Volume",
                "tx": "Total Trades",
                "btx": "Buy Trades"
            }, inplace=True)

            # Guardar en una hoja del Excel
            df.to_excel(writer, sheet_name=interval, index=False)
            print(f"Datos de {interval} guardados.")

    writer.save()
    print("Archivo Excel creado: BTCUSDT_OHLCV.xlsx")

# Ejecutar la función principal
process_intervals()
 

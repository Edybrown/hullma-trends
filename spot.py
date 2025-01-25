import requests
import time
import pandas as pd
import json

# Constantes
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Sustituye con tu clave real
SYMBOL = "BTCUSDT.A"
BASE_URL = "https://api.coinalyze.net/v1/"
ENDPOINT = "ohlcv-history"
INTERVALS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}
MAX_LIMIT = 2000  # Máximo permitido por la API
OUTPUT_FILE = "BTCUSDT_OHLCV.xlsx"

def fetch_data(symbol, interval, limit, api_key):
    """Solicita datos de OHLCV a la API de Coinalyze."""
    try:
        # Calcular timestamps dinámicos
        to_timestamp = int(time.time())
        from_timestamp = to_timestamp - (limit * INTERVALS[interval])
        
        # Construcción de URL y parámetros
        url = f"{BASE_URL}{ENDPOINT}?api_key={api_key}"
        params = {
            "symbols": symbol,
            "interval": interval,
            "from": from_timestamp,
            "to": to_timestamp
        }
        
        # Realizar la solicitud
        response = requests.get(url, params=params)
        response.raise_for_status()  # Lanza excepción si la respuesta tiene error
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud para {interval}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON para {interval}: {e}")
        return None

def process_data(data):
    """Convierte la respuesta de la API en un DataFrame."""
    rows = []
    if data and isinstance(data, dict) and "history" in data:
        for record in data["history"]:
            rows.append({
                "Timestamp": record["t"],
                "Open": record["o"],
                "High": record["h"],
                "Low": record["l"],
                "Close": record["c"],
                "Volume": record["v"],
                "Buy Volume": record.get("bv", 0),
                "Trades": record.get("tx", 0),
                "Buy Trades": record.get("btx", 0)
            })
    return pd.DataFrame(rows)

def save_to_excel(dataframes):
    """Guarda múltiples DataFrames en un archivo Excel."""
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        for interval, df in dataframes.items():
            if not df.empty:
                df["Fecha"] = pd.to_datetime(df["Timestamp"], unit="s")
                df.drop(columns=["Timestamp"], inplace=True)
                df.to_excel(writer, sheet_name=interval, index=False)

def main():
    """Función principal para ejecutar el flujo completo."""
    dataframes = {}
    
    for interval in INTERVALS:
        print(f"Solicitando datos para {interval}...")
        data = fetch_data(SYMBOL, interval, MAX_LIMIT, API_KEY)
        if data:
            df = process_data(data)
            if not df.empty:
                dataframes[interval] = df
                print(f"Datos procesados para {interval}, total de filas: {len(df)}")
            else:
                print(f"No se encontraron datos para {interval}.")
        else:
            print(f"Error al obtener datos para {interval}.")
    
    if dataframes:
        print(f"Guardando datos en el archivo {OUTPUT_FILE}...")
        save_to_excel(dataframes)
        print("Archivo Excel creado con éxito.")
    else:
        print("No se generó ningún archivo, no se obtuvieron datos.")

# Ejecutar la función principal
if __name__ == "__main__":
    main()

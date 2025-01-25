import requests
import time
import pandas as pd

# Constantes
BASE_URL = "https://api.coinalyze.net/v1/ohlcv-history"
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Sustituye con tu clave de API
SYMBOL = "BTCUSDT.A"
INTERVALS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

def fetch_data(symbol, interval, start, end):
    """Solicita datos OHLCV de la API."""
    url = f"{BASE_URL}?symbols={symbol}&interval={interval}&from={start}&to={end}&apikey={API_KEY}"
    print(f"Solicitando datos de {symbol} con intervalo {interval}...")
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener datos: {response.status_code} - {response.text}")
        response.raise_for_status()

def process_intervals():
    """Procesa cada intervalo y guarda los datos en un archivo Excel."""
    writer = pd.ExcelWriter("BTCUSDT_OHLCV.xlsx", engine="xlsxwriter")
    
    for interval, seconds in INTERVALS.items():
        try:
            # Calcular rango de tiempo
            to_timestamp = int(time.time())
            from_timestamp = to_timestamp - (seconds * 2000)
            
            # Solicitar datos
            data = fetch_data(SYMBOL, interval, from_timestamp, to_timestamp)
            
            # Procesar los datos recibidos
            rows = []
            for record in data[0]["history"]:
                rows.append({
                    "Timestamp": record["t"],
                    "Open": record["o"],
                    "High": record["h"],
                    "Low": record["l"],
                    "Close": record["c"],
                    "Volume": record["v"],
                    "Buy Volume": record["bv"],
                    "Trades": record["tx"],
                    "Buy Trades": record["btx"]
                })
            
            # Convertir a DataFrame y guardar en una hoja de Excel
            df = pd.DataFrame(rows)
            df["Fecha"] = pd.to_datetime(df["Timestamp"], unit="s")
            df.drop(columns=["Timestamp"], inplace=True)
            df.to_excel(writer, sheet_name=interval, index=False)
            
            print(f"Datos para {interval} procesados correctamente.")
        except Exception as e:
            print(f"Error al procesar el intervalo {interval}: {e}")

    writer.close()
    print("Archivo BTCUSDT_OHLCV.xlsx creado con éxito.")

# Ejecutar el procesamiento
process_intervals()

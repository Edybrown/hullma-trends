import requests
import pandas as pd
import time

# Definir la API Key y el endpoint base
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Reemplaza con tu API Key
BASE_URL = "https://api.coinalyze.net/v1/ohlcv-history"

# Función para realizar la solicitud a la API
def fetch_data(symbol, interval, start, end):
    url = f"{BASE_URL}?symbols={symbol}&interval={interval}&from={start}&to={end}&apikey={API_KEY}"
    response = requests.get(url)
    response.raise_for_status()  # Lanza un error si hay problemas con la solicitud
    return response.json()

# Función para procesar las temporalidades
def process_intervals():
    symbol = "BTCUSDT.A"  # Símbolo para la solicitud
    intervals = ["1hour", "4hour", "daily"]  # Temporalidades deseadas
    max_candles = 2000  # Número máximo de velas
    current_time = int(time.time())  # Tiempo actual en segundos
    
    # Crear un archivo Excel para guardar los datos
    writer = pd.ExcelWriter("BTCUSDT_OHLCV.xlsx", engine="xlsxwriter")

    for interval in intervals:
        # Determinar el tiempo inicial basado en la cantidad máxima de velas
        if interval == "1hour":
            start_time = current_time - (3600 * max_candles)
        elif interval == "4hour":
            start_time = current_time - (3600 * 4 * max_candles)
        elif interval == "daily":
            start_time = current_time - (86400 * max_candles)

        # Llamar a la API para obtener los datos
        try:
            print(f"Solicitando datos para {interval}...")
            data = fetch_data(symbol, interval, start_time, current_time)
            history = data[0]["history"]

            # Convertir los datos en un DataFrame
            df = pd.DataFrame(history)
            df["t"] = pd.to_datetime(df["t"], unit="s")  # Convertir timestamp a fecha
            df.rename(
                columns={
                    "t": "Timestamp",
                    "o": "Open",
                    "h": "High",
                    "l": "Low",
                    "c": "Close",
                    "v": "Total Volume",
                    "bv": "Buy Volume",
                    "tx": "Total Trades",
                    "btx": "Buy Trades",
                },
                inplace=True,
            )

            # Guardar los datos en una hoja de Excel
            df.to_excel(writer, sheet_name=interval, index=False)
            print(f"Datos para {interval} guardados con éxito.")

        except Exception as e:
            print(f"Error al procesar el intervalo {interval}: {e}")

    # Guardar el archivo Excel
    writer.close()
    print("Archivo BTCUSDT_OHLCV.xlsx creado con éxito.")

# Ejecutar la función principal
if __name__ == "__main__":
    process_intervals()

import requests
import time
import openpyxl
import logging
from datetime import datetime, timezone

# Configuration for logging
logging.basicConfig(filename='coinalyze_data.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Replace with your actual Coinalyze API key
SYMBOL = "BTCUSDT.A"
INTERVALS = ["4hour", "1hour", "daily"]


def get_ohlcv_data(symbol, interval):
    logging.info(f"Obteniendo datos OHLCV para {symbol} ({interval})")
    base_url = "https://api.coinalyze.net/v1/ohlcv-history"
    current_timestamp = int(time.time())
    interval_seconds = {
        "4hour": 14400,
        "1hour": 3600,
        "daily": 86400,
    }[interval]

    # Calculate timestamps for requested range (consider API requirements)
    now = datetime.now(timezone.utc)
    from_date = now - datetime.timedelta(seconds=2000 * interval_seconds)
    to_date = now

    logging.info(f"Solicitando datos desde: {from_date.isoformat()} hasta: {to_date.isoformat()}")

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": int(from_date.timestamp()),  # Convert to Unix timestamp if required
        "to": int(to_date.timestamp()),     # Convert to Unix timestamp if required
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "history" in data:
            return data["history"]
        else:
            logging.warning(f"No se encontraron datos históricos para {symbol} ({interval}). Respuesta: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener datos: {e}")
        return None

def save_to_excel(data, filename):
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    # Encabezados
    headers = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    for col_num, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=col_num, value=header)

    # Escribe los datos
    if data:
        for row_num, item in enumerate(data, start=2):
            sheet.cell(row=row_num, column=1, value=item["t"])  # Timestamp
            sheet.cell(row=row_num, column=2, value=item["o"])  # Open
            sheet.cell(row=row_num, column=3, value=item["h"])  # High
            sheet.cell(row=row_num, column=4, value=item["l"])  # Low
            sheet.cell(row=row_num, column=5, value=item["c"])  # Close
            sheet.cell(row=row_num, column=6, value=item["v"])  # Volume
            sheet.cell(row=row_num, column=7, value=item["bv"]) # Base Volume
            sheet.cell(row=row_num, column=8, value=item["tx"]) # Transactions
            sheet.cell(row=row_num, column=9, value=item["btx"])# Base Transactions
    else:
        logging.warning("No hay datos para guardar en Excel.")

    workbook.save(filename)
    logging.info(f"Datos guardados en {filename}")

# Ejecutar
for interval in INTERVALS:
    ohlcv_data = get_ohlcv_data(SYMBOL, interval)
    if ohlcv_data:
        filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
        save_to_excel(ohlcv_data, filename)

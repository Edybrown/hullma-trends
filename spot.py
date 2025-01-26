import requests
import time
import json
import openpyxl
import logging

# Configuración del logging
logging.basicConfig(filename='coinalyze_data.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # ¡REEMPLAZA ESTO CON TU CLAVE REAL!
SYMBOL = "BTCUSDT_PERP.A"
INTERVALS = ["4hour", "1hour", "daily"]
LIMIT = 2000

def get_ohlcv_data(symbol, interval, limit):
    logging.info(f"Obteniendo datos OHLCV para {symbol} ({interval}) con límite {limit}")
    base_url = "https://api.coinalyze.net/v1/ohlcv-history"
    current_timestamp = int(time.time())
    interval_seconds = {
        "4hour": 14400,
        "1hour": 3600,
        "daily": 86400,
    }[interval]
    from_timestamp = current_timestamp - (limit - 1) * interval_seconds

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": current_timestamp,
        "limit": limit,
    }

    logging.debug(f"URL de la solicitud: {base_url}")
    logging.debug(f"Parámetros de la solicitud: {params}")

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        logging.debug(f"Código de estado de la respuesta: {response.status_code}")

        try:
            data = response.json()
            logging.debug(f"Datos JSON recibidos: {data}")

            if isinstance(data, list) and len(data) > 0 and "history" in data[0]:
                logging.info(f"Datos OHLCV recibidos correctamente para {symbol} ({interval})")
                return data[0]["history"]
            else:
                logging.warning(f"Estructura de respuesta inesperada para {symbol} ({interval}): {data}")
                return None
        except json.JSONDecodeError as e:
            logging.error(f"Error al decodificar JSON para {symbol} ({interval}): {e}. Texto de la respuesta: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud para {symbol} ({interval}): {e}")
        if 'response' in locals() and response is not None:
            logging.error(f"Código de estado recibido: {response.status_code}")
            logging.error(f"Texto de la respuesta: {response.text}")
        return None



def save_to_excel(data, filename):
    logging.info(f"Guardando datos en Excel: {filename}")
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    header = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    sheet.append(header)

    if data:
        for item in data:
            row = [item.get("t"), item.get("o"), item.get("h"), item.get("l"), item.get("c"), item.get("v"), item.get("bv"), item.get("tx"), item.get("btx")]
            sheet.append(row)
    else:
        logging.warning("No hay datos para guardar en Excel.")

    try:
        workbook.save(filename)
        logging.info(f"Datos OHLCV guardados en '{filename}'.")
    except Exception as e:
        logging.error(f"Error al guardar el archivo Excel: {e}")

# Main execution
all_data = {}
for interval in INTERVALS:
    ohlcv_data = get_ohlcv_data(SYMBOL, interval, LIMIT)
    if ohlcv_data:
        all_data[interval] = ohlcv_data

if all_data:
    for interval, data in all_data.items():
        filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
        save_to_excel(data, filename)
else:
    logging.warning("No se pudieron recuperar datos OHLCV para ningún intervalo.")

logging.info("Proceso completado.")

import requests
import time
import openpyxl
import logging
from datetime import datetime, timezone

# Configuración del logging
logging.basicConfig(filename='coinalyze_data.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # ¡REEMPLAZA ESTO CON TU CLAVE REAL!
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

    # Calcula los timestamps para el rango solicitado
    now = datetime.now(timezone.utc)
    from_date = now - datetime.timedelta(seconds=2000 * interval_seconds)
    to_date = now

    logging.info(f"Solicitando datos desde: {from_date.isoformat()} hasta: {to_date.isoformat()}")

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": int(from_date.timestamp()),
        "to": int(to_date.timestamp()),
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        logging.debug(f"Código de estado de la respuesta: {response.status_code}")
        try:
            data = response.json()
            logging.debug(f"Datos JSON recibidos: {data}")
            if isinstance(data, list):  # Verifica si la respuesta es una lista
                logging.info(f"Datos OHLCV recibidos correctamente para {symbol} ({interval})")
                return data
            else:
                logging.warning(f"Estructura de respuesta inesperada para {symbol} ({interval}): {data}")
                return None
        except json.JSONDecodeError as e:
            logging.error(f"Error al decodificar JSON para {symbol} ({interval}): {e}. Texto de la respuesta: {response.text if 'response' in locals() else 'No response text'}")
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

    # Encabezados
    headers = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    sheet.append(headers)

    if data:
        for item in data:
            row = [item.get("t"), item.get("o"), item.get("h"), item.get("l"), item.get("c"), item.get("v"), item.get("bv"), item.get("tx"), item.get("btx")]
            sheet.append(row)
    else:
        logging.warning("No hay datos para guardar en Excel.")

    try:
        workbook.save(filename)
        logging.info(f"Datos guardados en {filename}")
    except Exception as e:
        logging.error(f"Error al guardar el archivo Excel: {e}")


# Ejecutar
for interval in INTERVALS:
    ohlcv_data = get_ohlcv_data(SYMBOL, interval)
    if ohlcv_data:
        filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
        save_to_excel(ohlcv_data, filename)

logging.info("Proceso completado.")

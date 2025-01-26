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

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        print(f"Conexión exitosa: {response.status_code}")  # Confirmación de conexión en consola
        logging.info(f"Conexión exitosa para {symbol} ({interval})")
        
        data = response.json()

        # Verifica que "history" está presente dentro de la respuesta
        if "history" in data:
            history = data["history"]
            if isinstance(history, list):
                logging.info(f"Datos OHLCV recibidos correctamente para {symbol} ({interval})")
                return history
            else:
                logging.warning(f"Estructura de 'history' inesperada: {history}")
                return None
        else:
            logging.warning(f"Respuesta sin 'history' para {symbol} ({interval}): {data}")
            return None

    except json.JSONDecodeError as e:
        logging.error(f"Error al decodificar JSON para {symbol} ({interval}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud para {symbol} ({interval}): {e}")
        return None


def save_to_excel(data, filename):
    logging.info(f"Guardando datos en Excel: {filename}")
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    # Encabezados
    header = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    sheet.append(header)

    if data:
        for item in data:
            row = [
                item.get("t"),  # Timestamp
                item.get("o"),  # Open
                item.get("h"),  # High
                item.get("l"),  # Low
                item.get("c"),  # Close
                item.get("v"),  # Volume
                item.get("bv"), # Base Volume
                item.get("tx"), # Transactions
                item.get("btx") # Base Transactions
            ]
            sheet.append(row)
    else:
        logging.warning("No hay datos para guardar en Excel.")

    try:
        workbook.save(filename)
        logging.info(f"Datos OHLCV guardados en '{filename}'.")
    except Exception as e:
        logging.error(f"Error al guardar el archivo Excel: {e}")

# Ejecución principal
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
print("Proceso completado. Los datos se han guardado en archivos Excel.")

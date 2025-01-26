import requests
import time
import json
import openpyxl
import logging

# Configuración del logging
logging.basicConfig(filename='coinalyze_data.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # ¡REEMPLAZA ESTO CON TU CLAVE REAL!
SYMBOL = "BTCUSDT.A"
INTERVALS = ["4hour", "1hour", "daily"]
SESSIONS = 2000  # Número de sesiones deseadas

def get_ohlcv_data(symbol, interval, sessions):
    logging.info(f"Obteniendo datos OHLCV para {symbol} ({interval}) con {sessions} sesiones")
    base_url = "https://api.coinalyze.net/v1/ohlcv-history"

    # Calcular timestamps basados en las sesiones deseadas
    current_timestamp = int(time.time())
    interval_seconds = {
        "4hour": 14400,  # 4 horas en segundos
        "1hour": 3600,   # 1 hora en segundos
        "daily": 86400,  # 1 día en segundos
    }[interval]

    from_timestamp = current_timestamp - (sessions * interval_seconds)

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": current_timestamp,
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
    headers = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    for col_num, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=col_num, value=header)

    # Escribe los datos en celdas específicas
    if data:
        for row_num, item in enumerate(data, start=2):
            sheet.cell(row=row_num, column=1, value=item.get("t"))  # Timestamp
            sheet.cell(row=row_num, column=2, value=item.get("o"))  # Open
            sheet.cell(row=row_num, column=3, value=item.get("h"))  # High
            sheet.cell(row=row_num, column=4, value=item.get("l"))  # Low
            sheet.cell(row=row_num, column=5, value=item.get("c"))  # Close
            sheet.cell(row=row_num, column=6, value=item.get("v"))  # Volume
            sheet.cell(row=row_num, column=7, value=item.get("bv")) # Base Volume
            sheet.cell(row=row_num, column=8, value=item.get("tx")) # Transactions
            sheet.cell(row=row_num, column=9, value=item.get("btx"))# Base Transactions
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
    ohlcv_data = get_ohlcv_data(SYMBOL, interval, SESSIONS)
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

import requests
import time
import json
import openpyxl
import logging
from datetime import datetime, timezone, timedelta
from openpyxl.utils import get_column_letter

# Configuración del logging
logging.basicConfig(
    filename='coinalyze_data.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # ¡REEMPLAZA ESTO CON TU CLAVE REAL!
SYMBOL = "BTCUSDT.A"
INTERVALS = ["4hour", "1hour", "daily"]

def get_ohlcv_data(symbol, interval):
    logging.info(f"Obteniendo datos OHLCV para {symbol} ({interval})")
    base_url = "https://api.coinalyze.net/v1/ohlcv-history"
    interval_seconds = {
        "4hour": 14400,
        "1hour": 3600,
        "daily": 86400,
    }[interval]

    # Calcula los timestamps para el rango solicitado
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(seconds=2000 * interval_seconds)
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
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            logging.info(f"Datos OHLCV recibidos correctamente para {symbol} ({interval})")
            return data
        else:
            logging.warning(f"Estructura de respuesta inesperada para {symbol} ({interval}): {data}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud para {symbol} ({interval}): {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Código de estado recibido: {e.response.status_code}")
            logging.error(f"Texto de la respuesta: {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error al decodificar JSON para {symbol} ({interval}): {e}")
        return None

def save_to_excel(data, filename):
    logging.info(f"Guardando datos en Excel: {filename}")
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    # Encabezados
    headers = ["Timestamp (UNIX)", "Open", "High", "Low", "Close", "Volume", "Base Volume", "Transactions", "Base Transactions"]
    for col, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=col, value=header)

    if data:
        for row, item in enumerate(data, start=2):
            sheet.cell(row=row, column=1, value=item.get("t"))
            sheet.cell(row=row, column=2, value=item.get("o"))
            sheet.cell(row=row, column=3, value=item.get("h"))
            sheet.cell(row=row, column=4, value=item.get("l"))
            sheet.cell(row=row, column=5, value=item.get("c"))
            sheet.cell(row=row, column=6, value=item.get("v"))
            sheet.cell(row=row, column=7, value=item.get("bv"))
            sheet.cell(row=row, column=8, value=item.get("tx"))
            sheet.cell(row=row, column=9, value=item.get("btx"))
        
        # Ajustar el ancho de las columnas
        for column in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            sheet.column_dimensions[column_letter].width = adjusted_width

        logging.info(f"Se guardaron {len(data)} registros en {filename}")
    else:
        logging.warning(f"No hay datos para guardar en Excel: {filename}")

    try:
        workbook.save(filename)
        logging.info(f"Archivo Excel guardado: {filename}")
    except Exception as e:
        logging.error(f"Error al guardar el archivo Excel {filename}: {e}")

# Ejecutar
if __name__ == "__main__":
    for interval in INTERVALS:
        ohlcv_data = get_ohlcv_data(SYMBOL, interval)
        if ohlcv_data:
            filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
            save_to_excel(ohlcv_data, filename)
        else:
            logging.warning(f"No se obtuvieron datos para {SYMBOL} en el intervalo {interval}")

    logging.info("Proceso completado.")

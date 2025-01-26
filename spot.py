import requests
import json
import openpyxl
import logging
from datetime import datetime, timezone, timedelta
from openpyxl.utils import get_column_letter

# Configuración del logging
logging.basicConfig(
    filename='btcspot',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Añadir logging a la consola
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Asegúrate de que esta sea tu API key correcta
SYMBOL = "BTCUSDT.A"
INTERVALS = ["4hour", "1hour", "daily"]

def get_ohlcv_data(symbol, interval):
    logging.info(f"Obteniendo datos OHLCV para {symbol} ({interval})")
    base_url = "https://api.coinalyze.net/v1/ohlcv-history"
    
    now = datetime.now(timezone.utc)
    to_date = int(now.timestamp())
    from_date = int((now - timedelta(days=30)).timestamp())  # Datos de los últimos 30 días

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_date,
        "to": to_date
    }

    try:
        logging.debug(f"Enviando solicitud a {base_url} con parámetros: {params}")
        response = requests.get(base_url, params=params)
        logging.debug(f"Código de estado de la respuesta: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"Estructura de datos recibidos: {json.dumps(data, indent=2)}")
        
        if isinstance(data, list) and len(data) > 0 and 'history' in data[0]:
            logging.info(f"Datos OHLCV recibidos correctamente para {symbol} ({interval}). Total de registros: {len(data[0]['history'])}")
            return data[0]['history']
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
        logging.error(f"Texto de la respuesta: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al obtener datos para {symbol} ({interval}): {e}")
        return None

def save_to_excel(data, filename):
    logging.info(f"Guardando datos en Excel: {filename}")
    workbook = openpyxl.Workbook()
    sheet = workbook.active

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

if __name__ == "__main__":
    logging.info("Iniciando el proceso de obtención y guardado de datos")
    try:
        for interval in INTERVALS:
            logging.info(f"Procesando intervalo: {interval}")
            ohlcv_data = get_ohlcv_data(SYMBOL, interval)
            if ohlcv_data:
                filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
                save_to_excel(ohlcv_data, filename)
            else:
                logging.warning(f"No se obtuvieron datos para {SYMBOL} en el intervalo {interval}")
        
        logging.info("Proceso completado con éxito")
    except Exception as e:
        logging.error(f"Error inesperado durante la ejecución del script: {e}")
        logging.exception("Detalles del error:")
    
    logging.info("Fin del script")

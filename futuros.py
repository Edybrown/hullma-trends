import requests
import os
import pandas as pd
from datetime import datetime
import json
import time
import pytz

# Parámetros generales
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOL_PERPETUOS = "BTCUSDT_PERP.A"
TEMPORALIDADES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "coinalyze_data"
VELAS = 2000
MAX_RETRIES = 5
RETRY_DELAY = 10
TIMEOUT = 30

# Crear la carpeta de salida
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TEMPORALIDAD_SEGUNDOS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

# Función para calcular los rangos de tiempo
def calcular_rango_temporalidad(temporalidad, velas):
    ahora = int(time.time())
    desde = ahora - (velas * TEMPORALIDAD_SEGUNDOS[temporalidad])
    return desde, ahora

# Función para obtener datos de la API
def fetch_data(endpoint, symbol, interval, from_timestamp, to_timestamp, convert_to_usd="false"):
    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"Obteniendo datos de {url}...")  # Mensaje de depuración

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            print(f"    Respuesta recibida de la API con código {response.status_code}")  # Depuración de estado

            try:
                data = response.json()
                if not isinstance(data, dict) or "history" not in data or not isinstance(data["history"], list):
                    print(f"WARNING: Estructura JSON inesperada para {endpoint} ({interval}): {data}")
                    return None
                return data
            except json.JSONDecodeError as e:
                print(f"Error al decodificar JSON para {endpoint} ({interval}): {e}. Respuesta: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Intento {attempt + 1}/{MAX_RETRIES} fallido para {endpoint} ({interval}): {e}")
            if response is not None:
                print(f"Código de estado: {response.status_code}")
                print(f"Texto de respuesta: {response.text}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    print(f"Fallo después de {MAX_RETRIES} intentos para {endpoint} ({interval})")
    return None

# Función para procesar y guardar los datos
def procesar_datos(data_types):
    output_folder = OUTPUT_FOLDER
    os.makedirs(output_folder, exist_ok=True)  # Crear la carpeta de salida

    for temporalidad in TEMPORALIDADES:
        print(f"Procesando datos para la temporalidad {temporalidad}...")

        for data_type, details in data_types.items():
            desde, hasta = calcular_rango_temporalidad(temporalidad, VELAS)
            print(f"  - Obteniendo datos para {data_type}...")

            # Obtener los datos de la API
            data = fetch_data(details["endpoint"], SYMBOL_PERPETUOS, temporalidad, desde, hasta)

            if not data:
                print(f"    WARNING: No se recibieron datos para {data_type} en {temporalidad}. Saltando.")
                continue

            try:
                # Verificar que los datos recibidos contienen la clave "history" y que no está vacía
                if "history" not in data or not data["history"]:
                    print(f"    WARNING: No se encontraron datos en 'history' para {data_type} en {temporalidad}. Saltando.")
                    continue

                # Crear el DataFrame a partir de la respuesta
                df = pd.DataFrame(data["history"])

                # Verificar que la columna 't' existe antes de convertirla
                if "t" not in df.columns:
                    print(f"    ERROR: La columna 't' no está presente en los datos de {data_type} en {temporalidad}.")
                    continue

                # Convertir el timestamp y establecer como índice
                df["timestamp"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_convert('America/New_York')
                df.set_index("timestamp", inplace=True)

                # Renombrar las columnas según la configuración proporcionada
                df.rename(columns=details["renames"], inplace=True)

                # Crear el nombre de archivo corto
                file_name = f"datos_{temporalidad}.csv"
                file_path = os.path.join(output_folder, file_name)

                # Guardar el DataFrame como archivo CSV
                df.to_csv(file_path)
                print(f"    Datos guardados exitosamente para {data_type} en {temporalidad}. Archivo: {file_name}")

            except (KeyError, ValueError, pd.errors.EmptyDataError) as e:
                print(f"    ERROR al procesar/guardar datos para {data_type} en {temporalidad}: {e}")
                if data and "history" in data:
                    print(f"    Ejemplo de datos recibidos: {data['history'][:5]}")  # Imprime los primeros 5 elementos
                elif data:
                    print(f"    Datos recibidos: {data}")

            except Exception as e:
                print(f"    ERROR inesperado al procesar/guardar datos para {data_type} en {temporalidad}: {e}")

    print("Proceso completado.")

# Diccionario con los tipos de datos a obtener y los detalles
data_types = {
    "ohlcv": {
        "endpoint": "ohlcv",
        "renames": {
            "t": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume"
        }
    },
    "open_interest": {
        "endpoint": "open_interest",
        "renames": {
            "t": "timestamp",
            "oi": "open_interest"
        }
    }
}

# Ejecutar el proceso
if __name__ == "__main__":
    print("Iniciando el proceso...")
    procesar_datos(data_types)

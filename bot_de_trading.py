 import requests

import logging

import time


# Configuración del logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Configuración general

API_URL = "https://api.phemex.com/exchange/public/md/v2/kline"

SYMBOL = "sBTCUSDT"  # Par de trading

RESOLUTION = 86400  # Resolución en segundos (1 día)

LIMIT = 100  # Límite de velas a recuperar

RETRY_DELAY = 60  # Tiempo de espera entre reintentos en segundos



def fetch_kline_data(symbol, resolution, limit):

    """

    Realiza una solicitud a la API pública de Phemex para obtener datos de Kline.


    Args:

        symbol (str): El par de trading, por ejemplo, "sBTCUSDT".

        resolution (int): Resolución de las velas en segundos.

        limit (int): Número máximo de velas a obtener.


    Returns:

        dict | None: Respuesta JSON con los datos de Kline si la solicitud es exitosa, None en caso de error.

    """

    params = {

        "symbol": symbol,

        "resolution": resolution,

        "limit": limit

    }


    try:

        response = requests.get(API_URL, params=params)

        response_data = response.json()


        if response.status_code == 200:

            logging.info("Datos de Kline recibidos correctamente.")

            return response_data

        else:

            logging.error(f"Error en la solicitud GET {API_URL}: {response.status_code} - {response_data}")

            return None


    except requests.exceptions.RequestException as e:

        logging.error(f"Excepción al realizar la solicitud GET: {e}")

        return None



def process_kline_data(data):

    """

    Procesa y muestra los datos de Kline obtenidos de la API.


    Args:

        data (dict): Datos de Kline en formato JSON.

    """

    if not data or "result" not in data or "rows" not in data["result"]:

        logging.warning("Datos de Kline inválidos o vacíos.")

        return


    rows = data["result"]["rows"]

    logging.info(f"Se recibieron {len(rows)} velas de datos.")


    # Imprimir las primeras 5 velas como ejemplo

    for i, row in enumerate(rows[:5]):

        timestamp = row["timestamp"]

        open_price = row["open"]

        high_price = row["high"]

        low_price = row["low"]

        close_price = row["close"]

        volume = row["volume"]


        logging.info(f"Vela {i + 1}: Timestamp: {timestamp}, Open: {open_price}, High: {high_price}, Low: {low_price}, Close: {close_price}, Volume: {volume}")



def main():

    """

    Función principal que ejecuta el ciclo del bot para obtener y procesar datos de Kline.

    """

    while True:

        logging.info("Iniciando nuevo ciclo del bot.")


        # Obtener datos de Kline

        data = fetch_kline_data(SYMBOL, RESOLUTION, LIMIT)


        if data:

            process_kline_data(data)

        else:

            logging.warning("No se pudieron obtener datos. Reintentando en el próximo ciclo.")


        # Esperar antes del próximo ciclo

        logging.info(f"Esperando {RETRY_DELAY} segundos antes del próximo ciclo.")

        time.sleep(RETRY_DELAY)



if __name__ == "__main__":

    main()

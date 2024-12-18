import websocket
import json
import time
import hmac
import hashlib
import requests
import logging
import os
import sys
import gzip
import signal
import datetime
import pandas as pd
import numpy as np
import threading
import time
from ta.momentum import RSIIndicator
import random

server_time_offset = 0  # Diferencia entre la hora local y la del servidor


# Configuración del logging
LOG_DIR = "logs"  # Directorio para los logs
os.makedirs(LOG_DIR, exist_ok=True)  # Crea el directorio si no existe

log_file_path = os.path.join(LOG_DIR, "coinex_bot.log") #Ruta completa al archivo log

logging.basicConfig(filename=log_file_path, #Archivo
                    level=logging.INFO, #Nivel
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Manejador para la consola (opcional, pero útil para ver logs en la terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) #Nivel para la consola
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler) #Añadir a la configuracion

def conectar():
    try:
        ws = websocket.WebSocketApp("wss://socket.coinex.com/v2/spot",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever() #Esta linea es la que se encarga de mantener la conexion
        return ws #Retornamos el websocket
    except Exception as e:
        logging.error(f"Error al conectar: {e}")
        return None

def reconectar():
    """Maneja la reconexión con retroceso exponencial y límite."""
    attempts = 0
    start_time = time.time()
    while attempts < MAX_RETRIES and (time.time() - start_time) < MAX_WAIT_TIME:
        attempts += 1
        delay = (BASE_DELAY * (2 ** (attempts - 1))) + random.uniform(0, 1)  # Retroceso exponencial + jitter
        logging.info(f"Intentando reconectar (intento {attempts}/{MAX_RETRIES}) en {delay:.2f} segundos...")
        time.sleep(delay)
        ws = conectar() #Intentamos conectar de nuevo
        if ws: #Si la conexion es correcta
            logging.info("Reconexión exitosa.")
            return ws #Retornamos el nuevo websocket
    
    if attempts >= MAX_RETRIES:
        logging.error(f"Número máximo de reintentos ({MAX_RETRIES}) alcanzado. No se pudo reconectar.")
    elif (time.time() - start_time) >= MAX_WAIT_TIME:
        logging.error(f"Tiempo máximo de espera ({MAX_WAIT_TIME} segundos) alcanzado. No se pudo reconectar.")
    return None #Si no se pudo reconectar retornamos None

def on_close(ws, close_status_code, close_msg):
    logging.info(f"Conexión cerrada. Código: {close_status_code}, Mensaje: {close_msg}")
    logging.info("Iniciando proceso de reconexión...")
    new_ws = reconectar() #Intentamos reconectar y guardamos el nuevo websocket
    if new_ws: #Si la reconexion fue exitosa
        global ws #Hacemos que la variable ws sea global para poder modificarla
        ws = new_ws #Asignamos el nuevo websocket a la variable global ws
        logging.info("Reconexión completa. Bot continuando.")
    else:
        logging.error("Reconexión fallida. Bot detenido.")
        os._exit(1) #Forzamos la detencion del bot

def get_server_time(ws):
    global server_time_offset
    try:
        ws.send(json.dumps({"method": "server.time", "params": {}, "id": time.time()}))
        # ... (Recibir la respuesta y extraer el timestamp del servidor)
        server_time_from_server = ...  # El timestamp recibido del servidor
        local_time = time.time() * 1000 # Timestamp local en milisegundos
        server_time_offset = server_time_from_server - local_time
        logging.info(f"Hora del servidor obtenida, offset: {server_time_offset} ms")
    except Exception as e:
        logging.error(f"Error al obtener la hora del servidor: {e}")

def on_open(ws):
    logging.info("Conexión WebSocket abierta.")
    subscription_message = {
        "method": "state.subscribe",
        "params": {"market_list": ["BTCUSDT"]},
        "id": 1
    }
    try:
        ws.send(json.dumps(subscription_message))
        logging.info(f"Mensaje de suscripción enviado: {subscription_message}")
    except Exception as e:
        logging.error(f"Error al enviar el mensaje de suscripción: {e}")

def on_error(ws, error):
    logging.error(f"Error en la conexión WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info(f"Conexión WebSocket cerrada. Código: {close_status_code}, Mensaje: {close_msg}")

def on_message(ws, message):
    try:
        try:
            # Intenta descomprimir
            decompressed_message = gzip.decompress(message).decode('utf-8')
            logging.debug("Mensaje descomprimido exitosamente.")
        except (OSError, EOFError, zlib.error): #Captura las excepciones de descompresion
            # Si falla la descompresión, asume que el mensaje NO está comprimido
            decompressed_message = message.decode('utf-8')
            logging.debug("Mensaje NO comprimido, decodificado directamente.")

        try:
            data = json.loads(decompressed_message)
            print(data)
            # ... (procesamiento de datos)
        except json.JSONDecodeError as e:
            logging.error(f"Error al decodificar JSON: {e}. Mensaje original: {decompressed_message}")
        except Exception as e:
            logging.error(f"Error al procesar mensaje JSON: {e}")

    except UnicodeDecodeError as e:
        logging.error(f"Error de decodificación UTF-8 (fuera del gzip): {e}. Mensaje original (bytes): {message}")
    except Exception as e:
        logging.error(f"Error general en on_message: {e}") 
      
candles = {}  # Diccionario para almacenar las velas. Clave: timestamp de inicio (int), Valor: diccionario con datos de la vela
MAX_CANDLES = 100 # Maximo de velas a guardar

def hma(src, length):
        half_length = int(length / 2)
        sqrt_length = int(np.sqrt(length))

    # Cálculo CORRECTO de la WMA usando weights
        wma1 = src.rolling(half_length).apply(lambda x: np.average(x, weights=np.arange(1, half_length + 1)))
        wma2 = src.rolling(length).apply(lambda x: np.average(x, weights=np.arange(1, length + 1)))

        hma_result = 2 * wma1 - wma2
        return hma_result.rolling(sqrt_length).apply(lambda x: np.average(x, weights=np.arange(1, sqrt_length + 1)))


def calculate_indicators(market, candles_list):
    """Calcula RSI (rápido y lento) y HMA y genera señales."""
    if not candles_list or len(candles_list) < 25:
        logging.warning(f"No hay suficientes datos para calcular indicadores en {market}")
        return None

    try:  # Inicio del bloque try
        df = pd.DataFrame(candles_list)
        df = df.set_index('timestamp')
        close_prices = df['close']

        rsi_fast = RSIIndicator(close=close_prices, window=8).rsi()
        rsi_slow = RSIIndicator(close=close_prices, window=14).rsi()
        df['rsi_fast'] = rsi_fast
        df['rsi_slow'] = rsi_slow

        df['hma'] = hma(close_prices, 14)  # Línea 137 (ahora bien indentada)

        df['buy_signal'] = (df['rsi_fast'] > df['rsi_slow']) & (df['rsi_fast'].shift(1) <= df['rsi_slow'].shift(1)) & (df['close'] > df['hma'])
        df['sell_signal'] = (df['rsi_fast'] < df['rsi_slow']) & (df['rsi_fast'].shift(1) >= df['rsi_slow'].shift(1)) & (df['close'] < df['hma'])

        logging.info(f"Cálculo de indicadores y señales para {market} exitoso")
        return df

    except Exception as e:  # Bloque except (correctamente indentado al mismo nivel que el try)
        logging.error(f"Error al calcular indicadores o señales: {e}")
        return None

def on_message(ws, message):
    try:
        try:
            decompressed_message = gzip.decompress(message).decode('utf-8')
            logging.debug("Mensaje descomprimido exitosamente.")
        except (OSError, EOFError, zlib.error, UnicodeDecodeError):
            decompressed_message = message.decode('utf-8')
            logging.debug("Mensaje NO comprimido, decodificado directamente.")

        data = json.loads(decompressed_message)

        if data.get('method') == 'state.update':
            local_time = datetime.datetime.now(datetime.UTC)
            server_now = local_time + datetime.timedelta(milliseconds=server_time_offset)
            minute10_timestamp = server_now - datetime.timedelta(minutes=server_now.minute % 10, seconds=server_now.second, microseconds=server_now.microsecond)
            minute10_timestamp = int(minute10_timestamp.timestamp())
            state_list = data.get('data').get('state_list')

            if state_list:
                for state in state_list:
                    market = state.get('market')
                    last_price = float(state.get('last'))
                    volume = float(state.get('volume')) if state.get('volume') is not None else 0

                    if minute10_timestamp not in candles:
                        candles[minute10_timestamp] = {
                            'timestamp': minute10_timestamp,
                            'open': last_price,
                            'high': last_price,
                            'low': last_price,
                            'close': last_price,
                            'volume': volume
                        }
                        threading.Timer(600, calculate_indicators, args=[market, list(candles.values())]).start()
                        logging.info(f"Creando nueva vela para {market} a las {datetime.datetime.fromtimestamp(minute10_timestamp)}")
                    else:
                        candles[minute10_timestamp]['close'] = last_price
                        candles[minute10_timestamp]['high'] = max(candles[minute10_timestamp]['high'], last_price)
                        candles[minute10_timestamp]['low'] = min(candles[minute10_timestamp]['low'], last_price)
                        candles[minute10_timestamp]['volume'] += volume
                        logging.debug(f"Actualizando vela para {market} a las {datetime.datetime.fromtimestamp(minute10_timestamp)}, precio: {last_price}")

                while len(candles) > MAX_CANDLES:
                    oldest_candle = min(candles.keys())
                    del candles[oldest_candle]
                    logging.debug(f"Eliminando vela antigua con timestamp: {oldest_candle}")
            else:
                logging.warning("La lista de estados esta vacia")

        elif data.get('error'):
            logging.error(f"Error del servidor: {data.get('error')}")
        else:
            logging.debug(f"Mensaje recibido (otro tipo): {message}")

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.error(f"Error al procesar el mensaje: {e}. Mensaje original: {message!r}")
    except Exception as e:
        logging.error(f"Error inesperado en on_message: {e}")

if __name__ == "__main__": #Para que solo se ejecute esto al correr el script
   logging.info("Iniciando bot...")
    ws = conectar()
    if ws is None:
        logging.error("Fallo la conexion inicial. Bot detenido.")
        os._exit(1)
    logging.info("Bot en funcionamiento.")
    try:
        while True:
            time.sleep(1)
            #Aqui se puede agregar codigo para que el bot haga otras tareas
    except KeyboardInterrupt:
        logging.info("Bot detenido por el usuario.")
        ws.close()
        sys.exit()
    except Exception as e:
        logging.critical(f"Error critico en el loop principal del bot: {e}")
        ws.close()
        sys.exit()

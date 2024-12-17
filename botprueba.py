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

def on_message(ws, message):
    logging.debug(f"Mensaje recibido (sin procesar): {message}") #Log en debug para ver todos los msj
    try:
        data = json.loads(message)
        # *** Aquí va tu lógica de procesamiento del mensaje ***
        # Ejemplos:
        if "market" in data and "ticker" in data:
          logging.info(f"Actualización de mercado recibida: {data['market']}")
          #logging.debug(f"Datos del ticker: {data['ticker']}") #Datos detallados del ticker
        elif "error" in data:
          logging.error(f"Error recibido del servidor: {data['error']}")
        # ... otros procesamientos según la estructura de los mensajes de CoinEx
    except json.JSONDecodeError as e:
        logging.error(f"Error al decodificar JSON: {e}. Mensaje original: {message}")
    except Exception as e: #Captura otros posibles errores en el procesamiento del mensaje
      logging.error(f"Error al procesar mensaje: {e}")


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

def calculate_indicators(market, candles_list):
    """Calcula RSI (rápido y lento) y HMA y genera señales.

    Args:
        market: El mercado (ej. "BTCUSDT").
        candles_list: Lista de diccionarios de velas.

    Returns:
        DataFrame con indicadores y señales, o None si hay error.
    """
    if not candles_list or len(candles_list) < 25: # Necesito al menos 25 velas para HMA(24) + shift(1)
        logging.warning(f"No hay suficientes datos para calcular indicadores en {market}")
        return None

    try:
        df = pd.DataFrame(candles_list)
        df = df.set_index('timestamp')
        close_prices = df['close']

        # RSI rápido y lento (con ventanas distintas)
        rsi_fast = RSIIndicator(close=close_prices, window=8).rsi()
        rsi_slow = RSIIndicator(close=close_prices, window=14).rsi()
        df['rsi_fast'] = rsi_fast
        df['rsi_slow'] = rsi_slow

        # HMA (con corrección en el cálculo de la WMA)
        def hma(src, length):
            half_length = int(length / 2)
            sqrt_length = int(np.sqrt(length))
            wma1 = src.rolling(half_length).apply(lambda x: np.average(x, weights=np.arange(1, half_length + 1)))
            wma2 = src.rolling(length).apply(lambda x: np.average(x, weights=np.arange(1, length + 1)))
            hma_result = 2 * wma1 - wma2
            return hma_result.rolling(sqrt_length).apply(lambda x: np.average(x, weights=np.arange(1, sqrt_length + 1)))

        df['hma'] = hma(close_prices, 24)

        # GENERACIÓN DE SEÑALES (AHORA CORRECTAMENTE IMPLEMENTADA)
        df['buy_signal'] = (df['rsi_fast'] > df['rsi_slow']) & (df['rsi_fast'].shift(1) <= df['rsi_slow'].shift(1)) & (df['close'] > df['hma'])
        df['sell_signal'] = (df['rsi_fast'] < df['rsi_slow']) & (df['rsi_fast'].shift(1) >= df['rsi_slow'].shift(1)) & (df['close'] < df['hma'])

        logging.info(f"Cálculo de indicadores y señales para {market} exitoso")
        return df
    except Exception as e:
        logging.error(f"Error al calcular indicadores o señales: {e}")
        return None


def on_message(ws, message):
    try:
        # ... (descompresión y decodificación del mensaje - igual que antes)
        data = json.loads(decompressed_message)

        if data.get('method') == 'state.update':
            server_time = data.get('serverTime')
            if server_time is None:
                logging.warning("No se recibio serverTime, usando tiempo local")
                now = datetime.datetime.utcnow()
            else:
                now = datetime.datetime.utcfromtimestamp(server_time/1000)
            state_list = data.get('data').get('state_list')

            if state_list:
                for state in state_list:
                    market = state.get('market')
                    last_price = float(state.get('last'))
                    volume = float(state.get('volume')) if state.get('volume') is not None else 0

                    minute10_timestamp = now - datetime.timedelta(minutes=now.minute % 10, seconds=now.second, microseconds=now.microsecond)
                    minute10_timestamp = int(minute10_timestamp.timestamp())

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

                    # Eliminar velas antiguas si se excede el máximo
                    while len(candles) > MAX_CANDLES: #usando while para evitar que se salteen velas en caso de que el reloj se atrase mucho
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
    try:
        ws = websocket.WebSocketApp("wss://socket.coinex.com/v2/spot",
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        ws.run_forever()
    except Exception as e:
        logging.critical(f"Error crítico al iniciar el bot: {e}") #Error critico que detiene la app

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

MAX_RETRIES = 5
MAX_WAIT_TIME = 60
BASE_DELAY = 2

ws = None #Declaramos ws como global aqui

def obtener_historico(market, tipo_vela, limite=200):
    """Obtiene datos históricos de CoinEx usando la API REST."""
    url = f"https://api.coinex.com/v1/market/kline?market={market}&type={tipo_vela}&limit={limite}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        data = response.json()

        if data['code'] == 0:
            kline_data = data['data']
            # Convertir a DataFrame de pandas para facilitar el manejo
            df = pd.DataFrame(kline_data, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='s') #Convertimos el tiempo a datetime
            df[['open', 'close', 'high', 'low', 'volume']] = df[['open', 'close', 'high', 'low', 'volume']].astype(float)
            df = df.set_index('time')
            return df
        else:
          logging.error(f"Error al obtener datos históricos: {data['message']}")
          return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud HTTP: {e}")
        return None
    except (KeyError, TypeError) as e:
        logging.error(f"Error al procesar la respuesta JSON: {e}. Respuesta: {data}")
        return None
if df_historico is not None:
    print(df_historico)
    #Ahora puedes trabajar con tu dataframe
    #Por ejemplo calcular indicadores
    #RSI
    from ta.momentum import RSIIndicator
    rsi = RSIIndicator(df_historico['close'], window=14).rsi()
    df_historico['rsi'] = rsi
    print(df_historico)
else:
    logging.error("No se pudieron obtener los datos históricos.")
def construir_velas_10min(df_5min):
    """Construye velas de 10 minutos a partir de velas de 5 minutos."""
    if df_5min is None or df_5min.empty:
        logging.warning("DataFrame de 5 minutos vacío. No se pueden construir velas de 10 minutos.")
        return pd.DataFrame()

    try:
        df_10min = df_5min.resample('10T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        df_10min = df_10min.dropna() #Eliminamos las filas con valores nulos que se crean al resamplear
        return df_10min
    except Exception as e:
        logging.error(f"Error al construir velas de 10 minutos: {e}")
        return pd.DataFrame()  

def conectar():
    """Conecta al servidor WebSocket."""
    try:
        ws_nuevo = websocket.WebSocketApp(
            "wss://socket.coinex.com/v2/spot",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        return ws_nuevo
    except Exception as e:
        logging.error(f"Error al conectar: {e}")
        return None

def reconectar(max_retries=MAX_RETRIES, base_delay=BASE_DELAY, max_wait_time=MAX_WAIT_TIME):
    """Maneja la reconexión."""
    attempts = 0
    start_time = time.time()
    while attempts < max_retries and (time.time() - start_time) < max_wait_time:
        attempts += 1
        delay = (base_delay * (2 ** (attempts - 1))) + random.uniform(0, 1)
        logging.info(f"Intentando reconectar (intento {attempts}/{max_retries}) en {delay:.2f} segundos...")
        time.sleep(delay)
        ws_nuevo = conectar()
        if ws_nuevo:
            logging.info("Reconexión exitosa.")
            return ws_nuevo
    logging.error(f"Número máximo de reintentos ({max_retries}) alcanzado. No se pudo reconectar.")
    return None

def on_close(close_status_code, close_msg): #ws ya no es un parametro
    """Maneja el cierre de la conexión."""
    logging.info(f"Conexión WebSocket cerrada. Código: {close_status_code}, Mensaje: {close_msg}")
    logging.info("Iniciando proceso de reconexión...")
    global ws  # Declaración global DENTRO de on_close
    ws = reconectar()
    if ws is None:
        logging.error("Reconexión fallida. Bot detenido.")
        os._exit(1)
  
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
        "id": 1,
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
    logging.info("Iniciando proceso de reconexión...")
    return reconectar() #Retornamos el nuevo websocket

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



def calcular_indicadores(market, df_10min):
    """Calcula RSI y HMA y genera señales."""
    if df_10min is None or len(df_10min) < 25:
        logging.warning(f"No hay suficientes datos para calcular indicadores en {market}")
        return None

    try:
        close_prices = df_10min['close']
        rsi_fast = RSIIndicator(close=close_prices, window=8).rsi()
        rsi_slow = RSIIndicator(close=close_prices, window=14).rsi()
        df_10min['rsi_fast'] = rsi_fast
        df_10min['rsi_slow'] = rsi_slow
        df_10min['hma'] = hma(close_prices, 14)

        df_10min['buy_signal'] = (df_10min['rsi_fast'] > df_10min['rsi_slow']) & (df_10min['rsi_fast'].shift(1) <= df_10min['rsi_slow'].shift(1)) & (df_10min['close'] > df_10min['hma'])
        df_10min['sell_signal'] = (df_10min['rsi_fast'] < df_10min['rsi_slow']) & (df_10min['rsi_fast'].shift(1) >= df_10min['rsi_slow'].shift(1)) & (df_10min['close'] < df_10min['hma'])

        logging.info(f"Cálculo de indicadores y señales para {market} exitoso")
        return df_10min

    except Exception as e:
        logging.error(f"Error al calcular indicadores o señales: {e}")
        return None

def on_message(ws, message):
    """Procesa los mensajes recibidos del WebSocket."""
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
                        logging.info(f"Creando nueva vela para {market} a las {datetime.datetime.fromtimestamp(minute10_timestamp)}")
                    else:
                        candles[minute10_timestamp]['close'] = last_price
                        candles[minute10_timestamp]['high'] = max(candles[minute10_timestamp]['high'], last_price)
                        candles[minute10_timestamp]['low'] = min(candles[minute10_timestamp]['low'], last_price)
                        candles[minute10_timestamp]['volume'] += volume
                        logging.debug(f"Actualizando vela para {market} a las {datetime.datetime.fromtimestamp(minute10_timestamp)}, precio: {last_price}")
                    #Calculamos los indicadores despues de actualizar la vela
                    df_candles = pd.DataFrame.from_dict(candles, orient='index')
                    df_candles = df_candles.set_index('timestamp')
                    df_con_indicadores = calcular_indicadores(market, df_candles)
                    if df_con_indicadores is not None:
                        print("Datos con indicadores:")
                        print(df_con_indicadores)
                    else:
                        logging.warning("No se pudieron calcular los indicadores")
            else:
                logging.warning("La lista de estados está vacía")

            while len(candles) > MAX_CANDLES:
                oldest_candle = min(candles.keys())
                del candles[oldest_candle]
                logging.debug(f"Eliminando vela antigua con timestamp: {oldest_candle}")

        elif data.get('error'):
            logging.error(f"Error del servidor: {data.get('error')}")
        else:
            logging.debug(f"Mensaje recibido (otro tipo): {message}")

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.error(f"Error al procesar el mensaje: {e}. Mensaje original: {message!r}")
    except Exception as e:
        logging.error(f"Error inesperado en on_message: {e}")

  
if __name__ == "__main__":
    logging.info("Iniciando bot...")
    ws = conectar()

    if ws is None:
        logging.error("Fallo la conexión inicial. Bot detenido.")
        sys.exit(1)

    # *** BLOQUE MOVIDO Y MEJORADO (FUERA DEL BUCLE) ***
    market_inicial = "BTCUSDT"
    tipo_vela_inicial = "1m"
    limite_inicial = 200

    df_historico = obtener_historico(market_inicial, tipo_vela_inicial, limite_inicial)
    if df_historico is not None and not df_historico.empty:
        logging.info(f"Datos históricos iniciales de {market_inicial} ({tipo_vela_inicial}) obtenidos.")
        logging.debug(df_historico)

        try:
            rsi = RSIIndicator(df_historico['close'], window=14).rsi()
            df_historico['rsi'] = rsi
            logging.debug("RSI calculado:")
            logging.debug(df_historico)
        except KeyError as e:
            logging.error(f"Error de KeyError al calcular RSI: {e}. Asegúrate de que la columna 'close' existe en el DataFrame.")
            logging.debug(df_historico)
        except Exception as e:
            logging.error(f"Error al calcular el RSI inicial: {e}")
            logging.debug(df_historico)
    else:
        if df_historico is None:
            logging.error(f"No se pudieron obtener los datos históricos iniciales de {market_inicial} ({tipo_vela_inicial}).")
        elif df_historico.empty:
            logging.error(f"Se obtuvieron datos históricos de {market_inicial} ({tipo_vela_inicial}), pero el DataFrame está vacío.")
        logging.error("El bot continuará sin datos históricos iniciales.")
    logging.info("Bot en funcionamiento.")

    try:
        while True:  # Bucle principal
            if ws is None:
                logging.info("Intentando reconectar...")
                ws = conectar()
                if ws is None:
                    logging.error("Reconexión fallida. Esperando 5 segundos...")
                    time.sleep(5)
                    continue

            try:
                ws.run_forever(ping_interval=30, ping_timeout=10)
                logging.info("Conexión cerrada por el servidor. Intentando reconectar...")
                ws = None  # Reseteamos ws a None para que entre en el if ws is None
            except Exception as e:
                logging.error(f"Error en run_forever: {e}")
                ws = None  # Reseteamos ws a None para que entre en el if ws is None
                time.sleep(5)
                continue

    except KeyboardInterrupt:
        logging.info("Bot detenido por el usuario.")
        if ws:
            ws.close()
        sys.exit()

    except Exception as e:
        logging.critical(f"Error crítico en el bucle principal del bot: {e}")
        if ws:
            ws.close()
        sys.exit(1)

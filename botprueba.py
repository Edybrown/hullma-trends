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
from urllib.parse import urljoin, urlencode 

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


def obtener_historico(market, period, limit=200):  # Cambiado tipo_vela a period
    base_url ="https://api.coinex.com/v2/spot/kline" 
    params = {
        "market": market,
        "period": period,
        "limit": limit
    }
    url = urljoin(base_url, "?" + urlencode(params)) #Construye la url de forma segura
    logging.debug(f"URL de la solicitud: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['code'] == 0:
            kline_data = data['data']
            df = pd.DataFrame(kline_data, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
        # ... (resto del procesamiento del DataFrame, como convertir tipos de datos, etc.)
            return df  # Devuelve el DataFrame procesado
        else:
            logging.error(f"Error al obtener datos históricos: {data.get('message', 'Sin mensaje adicional')}, Código: {data['code']}")
            return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"Error HTTP: {e}")
        if e.response is not None:
            logging.error(f"Código de estado: {e.response.status_code}")
            try:
                error_data = e.response.json()
                logging.error(f"Detalles del error: {error_data}")
            except json.JSONDecodeError:
                logging.error(f"Texto de la respuesta: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud: {e}")
        return None
    except (KeyError, TypeError) as e:
        logging.error(f"Error al procesar la respuesta JSON: {e}")
        return Noneos)
        response.raise_for_status()
        data = response.json()
        if data["code"] != 0:
            logging.error(f"Error al obtener datos históricos: {data['message']}")
            return None

        # CONVERSIÓN INMEDIATA A FLOAT: Convertimos los precios a float *aquí mismo*
        klines = []
        for kline_data in data["data"]:
            try:
                kline = {
                    "market": kline_data["market"],
                    "created_at": kline_data["created_at"],
                    "open": float(kline_data["open"]),
                    "close": float(kline_data["close"]),
                    "high": float(kline_data["high"]),
                    "low": float(kline_data["low"]),
                    "volume": float(kline_data["volume"]),
                    "value": float(kline_data["value"])
                }
                klines.append(kline)
            except ValueError as e:
                logging.error(f"Error al convertir datos a float en datos históricos: {e}. Datos: {kline_data}")
                return None
        df = pd.DataFrame(klines)
        return df
    except requests.exceptions.HTTPError as e:
        logging.error(f"Error de conversión numérica en calcular_indicadores: {e}")
        print(f"Error de conversión numérica en calcular_indicadores: {e}") # Imprime el error para depuración
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error al calcular indicadores o señales: {e}")
        print(f"Error al calcular indicadores o señales: {e}") # Imprime el error para depuración
        return None

def procesar_datos_iniciales(market, period, limit=25):
    df_inicial = obtener_historico(market, period, limit)
    if df_inicial is None:
        logging.error(f"Error al obtener datos históricos iniciales para {market}")
        return None

    # Imprime el DataFrame *antes* de la conversión y *después* de obtenerlo de la API
    print("DataFrame inicial ANTES de la conversión:")
    print(df_inicial)
    print(df_inicial.dtypes) #Imprime los tipos de datos

    df_con_indicadores = calcular_indicadores(market, df_inicial.copy()) # Pasamos una copia para no modificar el original directamente
    return df_con_indicadores

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
    """Calcula la Hull Moving Average (HMA)"""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))
    
    # Cálculo de WMA utilizando pesos explícitos
    wma1 = src.rolling(half_length).apply(lambda x: np.average(x, weights=np.arange(1, half_length + 1)), raw=True)
    wma2 = src.rolling(length).apply(lambda x: np.average(x, weights=np.arange(1, length + 1)), raw=True)
    
    # Cálculo de HMA: WMA1 * 2 - WMA2
    hma_result = 2 * wma1 - wma2
    # Aplicamos la WMA a la raíz cuadrada de la longitud
    return hma_result.rolling(sqrt_length).apply(lambda x: np.average(x, weights=np.arange(1, sqrt_length + 1)), raw=True)

def calcular_rsi(data, period=14):
    """Calcula el RSI a partir de los datos de precios."""
    try:
        # Intenta convertir los datos a numéricos, manejando posibles errores
        data = pd.to_numeric(data, errors='raise')  # 'raise' lanza una excepción si falla la conversión
    except ValueError as e:
        logging.error(f"Error al convertir datos a numéricos para RSI: {e}")
        return None

    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # Manejo de división por cero
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

def calcular_indicadores(market, df_10min):
    """Calcula RSI y HMA y genera señales de compra/venta."""
    if df_10min is None or len(df_10min) < 25:
        logging.warning(f"No hay suficientes datos para calcular indicadores en {market}")
        return None

    try:
        # CONVERSIÓN CRÍTICA: Convertir 'close' a numérico *antes* de cualquier cálculo
        df_10min['close'] = pd.to_numeric(df_10min['close'], errors='raise')

        close_prices = df_10min['close']

        rsi_fast = calcular_rsi(close_prices, 8)
        rsi_slow = calcular_rsi(close_prices, 14)

        if rsi_fast is None or rsi_slow is None:
            logging.error(f"Error en el cálculo de RSI para {market}")
            return None

        df_10min['rsi_fast'] = rsi_fast
        df_10min['rsi_slow'] = rsi_slow

        df_10min['hma'] = hma(close_prices, 14)
        # Generación de señales de compra y venta
        df_10min['buy_signal'] = (df_10min['rsi_fast'] > df_10min['rsi_slow']) & \
                                 (df_10min['rsi_fast'].shift(1) <= df_10min['rsi_slow'].shift(1)) & \
                                 (df_10min['close'] > df_10min['hma'])
        df_10min['sell_signal'] = (df_10min['rsi_fast'] < df_10min['rsi_slow']) & \
                                  (df_10min['rsi_fast'].shift(1) >= df_10min['rsi_slow'].shift(1)) & \
                                  (df_10min['close'] < df_10min['hma'])

        logging.info(f"Cálculo de indicadores y señales para {market} exitoso")
        return df_10min

    except ValueError as e: # Captura errores de conversion a numerico en calcular_indicadores
        logging.error(f"Error de conversión numérica en calcular_indicadores: {e}")
        return None
    except Exception as e:
        logging.error(f"Error al calcular indicadores o señales: {e}")
        return None

def procesar_datos_iniciales(market, period, limit=25): # Función para procesar los datos *iniciales*
    df_inicial = obtener_historico(market, period, limit)
    if df_inicial is None:
        logging.error(f"Error al obtener datos históricos iniciales para {market}")
        return None
    try:
        df_inicial['close'] = pd.to_numeric(df_inicial['close'], errors='raise') #CONVERSIÓN CRÍTICA AQUÍ
        df_con_indicadores = calcular_indicadores(market, df_inicial) # Calculamos los indicadores
        return df_con_indicadores
    except ValueError as e:
        logging.error(f"Error de conversión numérica en datos iniciales de {market}: {e}")
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

else:  # Este else corresponde al primer if
    if df_historico is None:
        logging.error(f"No se pudieron obtener los datos históricos iniciales de {market_inicial} ({tipo_vela_inicial}).")
    elif df_historico.empty:
        logging.error(f"Se obtuvieron datos históricos de {market_inicial} ({tipo_vela_inicial}), pero el DataFrame está vacío.")
    logging.error("El bot continuará sin datos históricos iniciales.")

logging.info("Bot en funcionamiento.") #Esto está fuera del if/else

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
            ws = None
        except Exception as e:
            logging.error(f"Error en run_forever: {e}")
            ws = None
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

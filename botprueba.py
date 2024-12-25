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
import pandas as pd
import ta  # Asegúrate de instalar: pip install ta
import random


# Configuración (¡REEMPLAZA CON TUS CREDENCIALES!)
API_KEY = "2A8AE2B7B0D0458CBF00F06620FA4E7C"
SECRET_KEY = "958D43B4E07D47E8B84E7DEEA58AAF321818AB5A0452FA80"
MARKET = "BTCUSDT"  # Par de trading
TIMEFRAME = "1hour"  # Intervalo de las velas
RSI_FAST_PERIOD = 8
RSI_SLOW_PERIOD = 14
HMA_PERIOD = 12
STOP_LOSS_PERCENT = 0.01  # 1% de stop loss
MAX_CANDLES = 200  # Máximo número de velas a mantener en memoria
LOG_DIR = "logs"
CANDLES_FILE = "historical_candles.csv"  # Nombre del archivo para guardar las velas


# Configuración de Logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=os.path.join(LOG_DIR, "coinex_bot.log"), level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler)

server_time_offset = 0
candles = {}
df_historical = pd.DataFrame()
ws = None
order_in_progress = False  # To avoid multiple orders simultaneously
last_buy_price = None  # Precio de la última compra


# Funciones de la API de CoinEx
def get_coinex_signature(data, secret_key):
    m = hmac.new(secret_key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256)
    return m.hexdigest().upper()

def coinex_api_request(method, path, params=None):
    url = f"https://api.coinex.com/v2/{path}"
    headers = {'Content-Type': 'application/json'}
    if params:
        params['access_id'] = API_KEY
        params['tonce'] = int(time.time() * 1000)
        data = ""
        for key in sorted(params):
            data += str(key) + "=" + str(params[key]) + "&"
        data = data[:-1]
        signature = get_coinex_signature(data, SECRET_KEY)
        params['signature'] = signature
    try:
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=params, headers=headers)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la API de CoinEx: {e}. Response: {response.text if 'response' in locals() else 'No response'}")
        return None

def get_balance():
    try:
        response = coinex_api_request('GET', 'balance', {'asset': MARKET.replace('USDT', '')})
        if response and response['code'] == 0:
            return float(response['data'][MARKET.replace('USDT', '')]['available'])
        else:
            logging.error(f"Error al obtener el balance: {response}")
            return None
    except Exception as e:
        logging.error(f"Excepción al obtener el balance: {e}")
        return None


def place_order(side, amount):
    try:
        params = {
            'market': MARKET,
            'type': 'market',
            'amount': amount,
        }
        response = coinex_api_request('POST', 'order/market', params)
        if response and response['code'] == 0:
            return response['data']['order_id']
        else:
            logging.error(f"Error al colocar la orden {side}: {response}")
            return None
    except Exception as e:
        logging.error(f"Excepción al colocar la orden: {e}")
        return None
      

def get_historical_candles(market, timeframe):
  """
  Obtiene velas históricas para un mercado y timeframe específico.
  Excluyendo la última vela (incompleta) y manejando potenciales errores.

  Args:
      market (str): Nombre del mercado (ej: "BTCUSDT").
      timeframe (str): Período de las velas (ej: "1hour").

  Returns:
      pandas.DataFrame: DataFrame con las velas históricas o vacío si hay errores.
  """  

  path = "spot/kline"
  params = {
      "market": "BTCUSDT",
      "limit": 200,  # Solicita 200 velas
      "period": "1hour" }

  try:
      response = coinex_api_request('GET', path, params=params)

      if response and 'data' in response and response['data']:
          data = response['data']
          df = pd.DataFrame(data, columns=['open', 'close', 'high', 'low', 'volume', 'value', 'created_at'])

          numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'value']
          df[numeric_cols] = df[numeric_cols].astype(float)

          # *** Manejo del orden y exclusión de la última vela: ***
          df['timestamp'] = pd.to_datetime(df['created_at'], unit='s', errors='coerce')
          df.set_index('timestamp', inplace=True)

          # Invertir el DataFrame si las velas vienen en orden ascendente (consulta la API)
          # df = df.iloc[::-1]  # Descomenta si es necesario

          # Excluir la última vela (incompleta)
          df = df.iloc[:-1]  # Selecciona todas las filas excepto la última

          if df.empty:
              logging.warning(f"No hay suficientes datos para calcular indicadores despues de eliminar la ultima vela incompleta para {market} {timeframe}.")
              return pd.DataFrame()

          # Calcular RSI y MHull (ejemplo con RSI)
          df['rsi'] = talib.RSI(df['close'], timeperiod=14)

          # Cálculo de MHull (ejemplo simplificado, necesitas implementar la lógica completa)
          def hull_moving_average(data, window):
              wma1 = pd.Series(data).rolling(window=window).apply(lambda x: np.average(x, weights=np.arange(1, window+1)))
              wma2 = pd.Series(data).rolling(window=window*2).apply(lambda x: np.average(x, weights=np.arange(1, window*2+1)))
              diff = wma1 * 2 - wma2
              sqrt_window = int(np.sqrt(window))
              hma = pd.Series(diff).rolling(window=sqrt_window).apply(lambda x: np.average(x, weights=np.arange(1, sqrt_window+1)))
              return hma
          df['mhull'] = hull_moving_average(df['close'], 14)

          logging.info(f"Se procesaron {len(df)} velas históricas correctamente para {market} {timeframe}.")
          return df
      elif response and 'msg' in response:
          logging.error(f"Error al obtener velas históricas para {market} {timeframe}: {response['msg']}")
          return pd.DataFrame()
      else:
          logging.error(f"Respuesta inesperada de la API para {market} {timeframe}: {response}")
          return pd.DataFrame()

  except Exception as e:
      logging.exception(f"Excepción al obtener velas para {market} {timeframe}: {e}")
      return pd.DataFrame()

# Configuración del logging (puedes modificarla)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def calculate_indicators(df):
    if len(df) < max(RSI_FAST_PERIOD, RSI_SLOW_PERIOD, HMA_PERIOD):
        return None
    try:
        df['rsi_fast'] = ta.rsi(df['close'], RSI_FAST_PERIOD)
        df['rsi_slow'] = ta.rsi(df['close'], RSI_SLOW_PERIOD)
        df['hma'] = ta.hma(df['close'], HMA_PERIOD)
        return df
    except Exception as e:
        logging.error(f"Error al calcular indicadores: {e}")
        return None

# Funciones del WebSocket
def on_open(ws): #Definicion de on_open ANTES de usarlo
    logging.info("Conexión WebSocket abierta")
    subscribe_message_ticker = {
        "method": "subscribe",
        "params": ["ticker.BTCUSDT"],
        "id": 1
    }
    ws.send(json.dumps(subscribe_message_ticker))
    subscribe_message_kline = {
        "method": "subscribe",
        "params": ["kline_1hour.BTCUSDT"],
        "id": 2
    }
    ws.send(json.dumps(subscribe_message_kline))

def on_message(ws, message):
    global order_in_progress, last_buy_price, df_historical, candles
    try:
        decompressed_message = gzip.decompress(message).decode('utf-8') if isinstance(message, bytes) else message.decode('utf-8')
        data = json.loads(decompressed_message)

        if data.get('method') == 'state.update':
            state_list = data.get('data', {}).get('state_list', [])
            for state in state_list:
                if state.get('market') == MARKET:
                    last_price = float(state.get('last', 0))
                    timestamp = int(time.time()) // 3600 * 3600 #tiempo de la vela
                    if timestamp not in candles:
                        candles[timestamp] = {'open': last_price, 'high': last_price, 'low': last_price, 'close': last_price, 'volume': 0}
                    else:
                        candles[timestamp]['close'] = last_price
                        candles[timestamp]['high'] = max(candles[timestamp]['high'], last_price)
                        candles[timestamp]['low'] = min(candles[timestamp]['low'], last_price)
                        candles[timestamp]['volume'] = float(state.get('volume', candles[timestamp]['volume']))

            df = pd.DataFrame.from_dict(candles, orient='index')
            if not df.empty:
                df.index = pd.to_datetime(df.index, unit='s')
                df.index.name = 'time'
                df_historical = pd.concat([df_historical, df]).drop_duplicates().sort_index()
                df_historical = df_historical.last(MAX_CANDLES)

                df_historical.to_csv(CANDLES_FILE) #Guardar el archivo csv
                df_with_indicators = calculate_indicators(df_historical.copy())
                if df_with_indicators is not None:
                    check_signals(df_with_indicators)

    except (json.JSONDecodeError, UnicodeDecodeError, gzip.BadGzipFile) as e:
        logging.error(f"Error al procesar mensaje: {e}")


def check_signals(df):
    global order_in_progress, last_buy_price
    if order_in_progress or len(df) < 2:
        return

    last_row = df.iloc[-1]
    previous_row = df.iloc[-2]
    balance = get_balance()

    if balance is None:
        logging.error("No se pudo obtener el saldo. Imposible operar.")
        return

    # Lógica de COMPRA (sin cambios)
    if (last_row['rsi_fast'] > last_row['rsi_slow'] and
            previous_row['rsi_fast'] <= previous_row['rsi_slow'] and
            last_row['close'] > last_row['hma'] and last_buy_price is None):
        amount_usdt = balance
        if amount_usdt is not None:
            amount_btc = amount_usdt / last_row['close']
            if amount_btc * last_row['close'] > 0.0001:
                order_in_progress = True
                order_id = place_order('buy', amount_btc)
                if order_id:
                    logging.info(f"Compra ejecutada con order_id: {order_id}")
                    last_buy_price = last_row['close']
                else:
                    logging.error("Fallo al ejecutar la compra")
                order_in_progress = False
            else:
                logging.info("Cantidad de compra demasiado pequeña.")
        else:
            logging.error("No se pudo obtener el balance para calcular la cantidad de compra")
    # Nueva Lógica de VENTA
    elif last_buy_price is not None:  # Solo si se ha comprado antes
        current_price = last_row['close']
        stop_loss_price = last_buy_price * (1 - STOP_LOSS_PERCENT)
        if current_price <= stop_loss_price or (last_row['rsi_fast'] < last_row['rsi_slow'] and previous_row['rsi_fast'] >= previous_row['rsi_slow']): #Se añade la condicion del rsi para vender
            amount_btc = get_balance_btc() #Funcion para obtener el balance en btc
            if amount_btc is not None and amount_btc > 0:
                order_in_progress = True
                order_id = place_order('sell', amount_btc)
                if order_id:
                    logging.info(f"Venta ejecutada con order_id: {order_id} a precio {current_price}. Stop loss activado a {stop_loss_price if current_price <= stop_loss_price else 'señal RSI'}")
                    last_buy_price = None  # Resetear el precio de compra
                else:
                    logging.error("Fallo al ejecutar la venta")
                order_in_progress = False
            else:
                logging.info("No hay BTC para vender o saldo muy bajo.")
        else:
            logging.info(f"Esperando señal de venta. Precio actual: {current_price}, Stop Loss: {stop_loss_price}")

def get_balance_btc(): #Funcion para obtener el balance en btc
    try:
        response = coinex_api_request('GET', 'balance', {'asset': MARKET.replace('USDT', '')})
        if response and response['code'] == 0:
            return float(response['data'][MARKET.replace('USDT', '')]['available'])
        else:
            logging.error(f"Error al obtener el balance: {response}")
            return None
    except Exception as e:
        logging.error(f"Excepción al obtener el balance: {e}")
        return None
      
def on_message(ws, message):
    try:
        data = json.loads(message)
        if "method" in data:
            if data["method"] == "ticker.BTCUSDT": #Recibe la informacion del ticker
                ticker_data = data["params"][0]
                current_price = float(ticker_data["last"])
                logging.info(f"Precio actual de BTCUSDT: {current_price}")
                # ... (Aquí puedes usar current_price para tu lógica de trading)
            elif data["method"] == "kline_1hour.BTCUSDT": #Recibe la informacion de las velas de 1 hora
                kline_data = data["params"]
                logging.info(f"Datos de velas de 1 hora de BTCUSDT: {kline_data}")
                # ... (Aquí puedes usar kline_data para tu lógica de trading)
        else:
            logging.debug(f"Mensaje recibido: {message}")
    except json.JSONDecodeError:
        logging.error(f"Error al decodificar mensaje JSON: {message}")

def on_error(ws, error):
    logging.error(f"Error en la conexión WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info("Conexión WebSocket cerrada")
    if close_status_code or close_msg:
        logging.info(f"Código de cierre: {close_status_code}, Mensaje de cierre: {close_msg}")

def connect_websocket():
    global ws
    websocket_url = "wss://socket.coinex.com/v2/spot"
    while True:
        try:
            ws = websocket.WebSocketApp(websocket_url,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
            ws.run_forever(ping_interval=30)
        except Exception as e:
            logging.error(f"Error en la conexión WebSocket: {e}")
            logging.info("Intentando reconectar en 5 segundos...")
            time.sleep(5)

def main():
    try:
        logging.info("Iniciando bot de trading en CoinEx...")

        global df_historical
        if os.path.exists(CANDLES_FILE):  # Carga el archivo si existe
            try:
                df_historical = pd.read_csv(CANDLES_FILE, index_col='time', parse_dates=True)
                logging.info(f"Cargadas {len(df_historical)} velas desde {CANDLES_FILE}.")

            except pd.errors.EmptyDataError:
                logging.warning(f"El archivo {CANDLES_FILE} está vacío.")
            except FileNotFoundError:
                logging.warning(f"No se encontró el archivo {CANDLES_FILE}.")
            except Exception as e:
                logging.error(f"Error al leer el archivo {CANDLES_FILE}: {e}")

        if df_historical.empty: #Si esta vacio pide el historico
            df_historical = get_historical_candles(MARKET, TIMEFRAME)
            if df_historical is None or df_historical.empty:
                logging.error("No se pudieron obtener datos históricos. Saliendo...")
                sys.exit(1)
            else:
                logging.info(f"Se obtuvieron {len(df_historical)} velas históricas.")
                df_historical.to_csv(CANDLES_FILE)
        connect_websocket()

    except KeyboardInterrupt:
        logging.info("Cerrando el bot...")
        if ws:
            ws.close()
        sys.exit()
    except Exception as e:
        logging.error(f"Error principal: {e}")
        if ws:
            ws.close()
        sys.exit(1)

if __name__ == "__main__":  # ¡Esta línea es crucial!
    main()
              

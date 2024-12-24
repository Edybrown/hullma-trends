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

def get_historical_candles(market, timeframe, limit=MAX_CANDLES):
    path = f"/spot/kline?market={market}&limit={limit}&period={timeframe}" #Ruta y parametro corregidos
    response = coinex_api_request('GET', path)

    if response and response['code'] == 0:
        data = response['data']
        if data:
            df = pd.DataFrame(data, columns=['market','created_at','open', 'close', 'high', 'low', 'volume','value']) #Añadido los campos faltantes
            df['created_at'] = pd.to_datetime(df['created_at'], unit='ms') #Corregido a milisegundos
            df = df.set_index('created_at')
            df = df[['open', 'close', 'high', 'low', 'volume','value']].astype(float) #Seleccionado solo las columnas necesarias y convertidas a float
            return df
        else:
            logging.warning("La respuesta de la API contiene datos vacíos.")
            return pd.DataFrame()
    else:
        if response is not None and 'msg' in response:
            logging.error(f"Error al obtener velas históricas: {response['msg']}")
        else:
            logging.error(f"Error desconocido al obtener velas históricas: {response}")
        return None


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

    if (last_row['rsi_fast'] > last_row['rsi_slow'] and
            previous_row['rsi_fast'] <= previous_row['rsi_slow'] and
            last_row['close'] > last_row['hma'] and last_buy_price is None):
        amount_usdt = balance
        if amount_usdt is not None:  # Verificar que balance no sea None
            amount_btc = amount_usdt / last_row['close']
            if amount_btc * last_row['close'] > 0.0001:
                order_in_progress = True
                order_id = place_order('buy', amount_btc)
                if order_id:
                    logging.info(f"Compra ejecutada con order_id: {order_id}")
                    last_buy_price = last_row['close'] #Actualizar el precio de compra
                else:
                    logging.error("Fallo al ejecutar la compra")
                order_in_progress = False #Resetear la variable
            else:
                logging.info("Cantidad de compra demasiado pequeña.")
        else:
            logging.error("No se pudo obtener el balance para calcular la cantidad de compra")


def on_open(ws):
    logging.info("Conexión WebSocket abierta")
    subscribe_message = {
        "method": "state.subscribe",
        "params": [MARKET],
        "id": 1
    }
    ws.send(json.dumps(subscribe_message))

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
              

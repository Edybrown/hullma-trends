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
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import talib

# Configuración
API_KEY = "2A8AE2B7B0D0458CBF00F06620FA4E7C"
SECRET_KEY = "958D43B4E07D47E8B84E7DEEA58AAF321818AB5A0452FA80"
MARKET = "BTCUSDT"
TIMEFRAME = "1hour"
RSI_FAST_PERIOD = 8
RSI_SLOW_PERIOD = 14
HMA_PERIOD = 12
STOP_LOSS_PERCENT = 0.01
MAX_CANDLES = 200
LOG_DIR = "logs"
CANDLES_FILE = "historical_candles.csv"

# Configuración de Logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=os.path.join(LOG_DIR, "coinex_bot.log"), level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler)

def get_coinex_signature(data, secret_key):
    m = hmac.new(secret_key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256)
    return m.hexdigest().upper()

def coinex_api_request(method, path, params=None):
    url = f"https://api.coinex.com/v2/{path}"
    headers = {'Content-Type': 'application/json'}
    if params:
        params['access_id'] = API_KEY
        params['tonce'] = int(time.time() * 1000)
        data = "&".join([f"{key}={params[key]}" for key in sorted(params)])
        signature = get_coinex_signature(data, SECRET_KEY)
        params['signature'] = signature
    try:
        response = requests.request(method, url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la API de CoinEx: {e}")
        return None

def get_historical_candles(market, timeframe):
    path = "spot/kline"
    params = {
        "market": market,
        "limit": 200,
        "period":"1hour"
    }
    response = coinex_api_request('GET', path, params=params)
    if response and 'data' in response:
        # Asumimos que los datos vienen en este orden: [timestamp, open, close, high, low, volume, amount]
        df = pd.DataFrame(response['data'], columns=['timestamp', 'open', 'close', 'high', 'low', 'volume', 'amount'])
        
        # Convertir el timestamp a datetime
        df['time'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
        df.set_index('time', inplace=True)
        
        # Convertir las columnas numéricas a float
        numeric_columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
        df[numeric_columns] = df[numeric_columns].astype(float)
        
        # Eliminar la columna 'timestamp' original ya que ahora tenemos 'time' como índice
        df = df.drop(columns=['timestamp'])
        
        return df.sort_index()
    else:
        logging.error(f"No se pudieron obtener datos históricos: {response}")
        return pd.DataFrame()


def read_historical_data(file_path):
    try:
        # Intenta leer el archivo con 'time' como índice
        df = pd.read_csv(file_path, index_col='time', parse_dates=True)
    except ValueError:
        # Si 'time' no está en la lista, lee el archivo sin especificar un índice
        df = pd.read_csv(file_path)
        
        # Verifica si hay una columna que podría ser el tiempo
        time_column = None
        for col in df.columns:
            if 'time' in col.lower() or 'date' in col.lower():
                time_column = col
                break
        
        if time_column:
            # Si encontramos una columna de tiempo, la configuramos como índice
            df['time'] = pd.to_datetime(df[time_column])
            df.set_index('time', inplace=True)
            df = df.drop(columns=[time_column])
        else:
            # Si no hay columna de tiempo, creamos una basada en el índice
            df['time'] = pd.date_range(start='2024-01-01', periods=len(df), freq='H')
            df.set_index('time', inplace=True)
        
    # Asegurarse de que todas las columnas necesarias estén presentes
    required_columns = ['open', 'close', 'high', 'low', 'volume']
    for col in required_columns:
        if col not in df.columns:
            df[col] = 0.0  # o algún otro valor predeterminado apropiado
    
    return df

def calculate_hma(data, period):
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    wma1 = talib.WMA(data, timeperiod=half_period)
    wma2 = talib.WMA(data, timeperiod=period)
    diff = 2 * wma1 - wma2
    hma = talib.WMA(diff, timeperiod=sqrt_period)
    
    return hma

def calculate_indicators(df):
    df['rsi_fast'] = RSIIndicator(df['close'], window=RSI_FAST_PERIOD).rsi()
    df['rsi_slow'] = RSIIndicator(df['close'], window=RSI_SLOW_PERIOD).rsi()
    df['hma'] = calculate_hma(df['close'], HMA_PERIOD)
    return df

def generate_signals(df):
    df['signal'] = 0
    df.loc[(df['rsi_fast'] > df['rsi_slow']) & (df['close'] > df['hma']), 'signal'] = 1
    df.loc[(df['rsi_fast'] < df['rsi_slow']) & (df['close'] < df['hma']), 'signal'] = -1
    return df

def execute_trade(side, amount):
    params = {
        'market': MARKET,
        'type': 'market',
        'amount': amount,
    }
    response = coinex_api_request('POST', 'order/market', params)
    if response and response['code'] == 0:
        logging.info(f"Orden {side} ejecutada: {response['data']['order_id']}")
        return response['data']['order_id']
    else:
        logging.error(f"Error al ejecutar orden {side}: {response}")
        return None

def on_message(ws, message):
    global df_historical
    try:
        data = json.loads(gzip.decompress(message).decode('utf-8'))
        if 'method' in data:
            if data['method'] == 'ticker.update':
                ticker = data['params'][0]
                last_price = float(ticker['last'])
                logging.info(f"Último precio de {MARKET}: {last_price}")
                
                # Actualizar la última vela
                current_time = pd.Timestamp.now().floor('H')
                if current_time not in df_historical.index:
                    new_candle = pd.DataFrame(index=[current_time], data={
                        'open': last_price,
                        'high': last_price,
                        'low': last_price,
                        'close': last_price,
                        'volume': float(ticker['volume'])
                    })
                    df_historical = pd.concat([df_historical, new_candle]).sort_index()
                else:
                    df_historical.loc[current_time, 'close'] = last_price
                    df_historical.loc[current_time, 'high'] = max(df_historical.loc[current_time, 'high'], last_price)
                    df_historical.loc[current_time, 'low'] = min(df_historical.loc[current_time, 'low'], last_price)
                    df_historical.loc[current_time, 'volume'] = float(ticker['volume'])
                
                df_historical = df_historical.last(MAX_CANDLES)
                df_with_indicators = calculate_indicators(df_historical.copy())
                df_with_signals = generate_signals(df_with_indicators)
                
                last_signal = df_with_signals['signal'].iloc[-1]
                if last_signal != 0:
                    balance = float(coinex_api_request('GET', 'balance')['data']['USDT']['available'])
                    if last_signal == 1 and balance > 0:
                        amount = balance / last_price * 0.99  # 99% del balance disponible
                        execute_trade('buy', amount)
                    elif last_signal == -1:
                        balance_btc = float(coinex_api_request('GET', 'balance')['data']['BTC']['available'])
                        if balance_btc > 0:
                            execute_trade('sell', balance_btc)
                
                df_historical.to_csv(CANDLES_FILE)
                logging.info(f"Datos actualizados y guardados. Última señal: {last_signal}")
    except Exception as e:
        logging.error(f"Error al procesar mensaje: {e}")

def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info(f"Conexión WebSocket cerrada: {close_status_code} - {close_msg}")

def on_open(ws):
    logging.info("Conexión WebSocket abierta")
    subscribe_message = {
        "method": "subscribe",
        "params": [
            "ticker.BTCUSDT"
        ],
        "id": 1
    }
    ws.send(json.dumps(subscribe_message))

def run_websocket():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://socket.coinex.com/",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)
    ws.run_forever()

def main():
    try:
        logging.info("Iniciando bot de trading en CoinEx...")
        
        if os.path.exists(CANDLES_FILE):
            df_historical = read_historical_data(CANDLES_FILE)
            logging.info(f"Cargadas {len(df_historical)} velas desde {CANDLES_FILE}.")
        else:
            df_historical = get_historical_candles(MARKET, TIMEFRAME)
            if df_historical.empty:
                logging.error("No se pudieron obtener datos históricos. Saliendo...")
                sys.exit(1)
            logging.info(f"Se obtuvieron {len(df_historical)} velas históricas.")
            df_historical.to_csv(CANDLES_FILE)
        
        # Verificar y registrar la estructura del DataFrame
        logging.info(f"Columnas en df_historical: {df_historical.columns.tolist()}")
        logging.info(f"Índice de df_historical: {df_historical.index.name}")
        logging.info(f"Primeras filas de df_historical:\n{df_historical.head()}")
        
        run_websocket()
    except Exception as e:
        logging.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

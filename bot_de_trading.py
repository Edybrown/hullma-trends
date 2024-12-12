import logging
import time
import pandas as pd
import numpy as np
import hmac
import hashlib
import requests

# Configuración de logs
logging.basicConfig(
    filename="trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Configuración general
API_KEY = "13412340-2737-4953-879c-8ff573cafa7f"
API_SECRET = "uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU"
BASE_URL = "https://api.phemex.com"
SYMBOL = "sBTCUSDT"
TIMEFRAME = "5m"
STOP_LOSS_PERCENTAGE = 1.2

# Funciones auxiliares para la API

def generate_signature(method, path, expires, query_string=""):
    payload = f"{expires}{method}{path}{query_string}"
    return hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

def make_request(method, path, query_params=None, data=None):
    expires = int(time.time() * 1000) + 60000
    query_string = ""
    if query_params:
        query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])
    
    signature = generate_signature(method, path, expires, query_string)

    headers = {
        "x-phemex-access-token": API_KEY,
        "x-phemex-request-expiry": str(expires),
        "x-phemex-request-signature": signature
    }

    url = f"{BASE_URL}{path}"
    if query_string:
        url += f"?{query_string}"

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError("Unsupported HTTP method")

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error en la solicitud {method} {url}: {response.status_code} - {response.text}")
        return None

# Funciones específicas del bot

def fetch_data(symbol, timeframe):
    path = f"/md/kline"
    query_params = {
        "symbol": symbol,
        "resolution": timeframe,
        "limit": 100
    }
    response = make_request("GET", path, query_params)
    if response:
        candles = response.get("data", {}).get("rows", [])
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        return df
    return pd.DataFrame()

def fetch_balance():
    path = "/accounts/account"
    response = make_request("GET", path)
    if response:
        return response['data']['account']['accountBalanceEv'] / 1e8  # Convertir de satoshis a BTC
    return 0

def place_market_order(symbol, side, quantity):
    path = "/orders"
    data = {
        "symbol": symbol,
        "side": side.upper(),
        "ordType": "Market",
        "orderQty": int(quantity * 1e8)  # Convertir cantidad a satoshis
    }
    return make_request("POST", path, data=data)

def place_stop_loss_order(symbol, side, quantity, stop_price):
    path = "/orders"
    data = {
        "symbol": symbol,
        "side": side.upper(),
        "ordType": "StopMarket",
        "stopPx": int(stop_price * 1e8),  # Convertir precio a satoshis
        "orderQty": int(quantity * 1e8)  # Convertir cantidad a satoshis
    }
    return make_request("POST", path, data=data)

def hma(data, length):
    wma1 = data.rolling(window=int(length / 2)).mean()
    wma2 = data.rolling(window=length).mean()
    diff = 2 * wma1 - wma2
    return diff.rolling(window=int(np.sqrt(length))).mean()

def rsi(data, length):
    delta = data.diff(1)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=length).mean()
    avg_loss = pd.Series(loss).rolling(window=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_signals(data):
    data['hma_trend'] = hma(data['close'], 14)
    data['rsi_fast'] = rsi(data['close'], 14)
    data['rsi_slow'] = rsi(data['close'], 8)

    data['hma_signal'] = data['hma_trend'] > data['hma_trend'].shift(1)
    data['rsi_signal_buy'] = data['rsi_fast'] > data['rsi_slow']
    data['rsi_signal_sell'] = data['rsi_fast'] < data['rsi_slow']

    data['buy_signal'] = data['hma_signal'] & data['rsi_signal_buy']
    data['sell_signal'] = ~data['hma_signal'] & data['rsi_signal_sell']

    return data

def run_bot():
    trades = []
    position = None

    while True:
        try:
            logging.info("Iniciando nuevo ciclo del bot.")
            data = fetch_data(SYMBOL, TIMEFRAME)
            if data.empty:
                logging.warning("No se pudieron obtener datos de velas.")
                time.sleep(60)
                continue

            data = check_signals(data)
            latest = data.iloc[-1]

            balance = fetch_balance()
            if balance <= 0:
                logging.warning("Saldo insuficiente para operar.")
                time.sleep(60)
                continue

            quantity = balance / latest['close']

            if latest['buy_signal'] and position is None:
                logging.info("Señal de compra detectada.")
                order = place_market_order(SYMBOL, "buy", quantity)
                if order:
                    entry_price = latest['close']
                    stop_loss_price = entry_price * (1 - STOP_LOSS_PERCENTAGE / 100)
                    place_stop_loss_order(SYMBOL, "sell", quantity, stop_loss_price)

                    position = {
                        "side": "buy",
                        "entry_price": entry_price,
                        "timestamp": latest['timestamp']
                    }
                    trades.append(position)

            elif latest['sell_signal'] and position:
                logging.info("Señal de venta detectada.")
                order = place_market_order(SYMBOL, "sell", quantity)
                if order:
                    trades[-1]["exit_price"] = latest['close']
                    trades[-1]["exit_timestamp"] = latest['timestamp']
                    position = None

        except Exception as e:
            logging.error(f"Error en el ciclo del bot: {e}")

        time.sleep(60)

if __name__ == "__main__":
    run_bot()

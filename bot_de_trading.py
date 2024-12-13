import logging
import time
import pandas as pd
import requests
import json
import hmac
import hashlib

# Configuración de logs
logging.basicConfig(
    filename="trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Configuración general
API_KEY = '13412340-2737-4953-879c-8ff573cafa7f'
API_SECRET = 'uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU'
BASE_URL = "https://api.phemex.com"
SYMBOL = "sBTCUSDT"  # Asegúrate de usar el símbolo correcto
TIMEFRAME = 86400  # 1 día (86400 segundos)
STOP_LOSS_PERCENTAGE = 1.2

# Funciones auxiliares para la API
def generate_signature(method, path, query_string="", data=None):
    expires = str(int(time.time()) + 60000)  # Tiempo de expiración de la solicitud
    payload = f"{expires}{method}{path}{query_string}"

    if data:
        payload += json.dumps(data)  # Si tienes datos en el cuerpo de la solicitud

    signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return signature, expires

def make_request(method, path, query_params=None, data=None):
    expires = str(int(time.time()) + 60000)
    query_string = ""
    if query_params:
        query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])
    
    signature, expires = generate_signature(method, path, query_string, data)

    headers = {
        "x-phemex-access-token": API_KEY,
        "x-phemex-request-expiry": expires,
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

# Función de suscripción kline
def subscribe_to_kline(symbol, interval):
    url = f"{BASE_URL}/data/v2/subscribe"
    headers = {
        "x-phemex-access-token": API_KEY,
        "x-phemex-request-signature": API_SECRET,
    }

    # El cuerpo de la solicitud para suscribirse a las velas
    data = {
        "id": 0,
        "method": "kline.subscribe",
        "params": [
            symbol,  # Símbolo como "sBTCUSDT"
            interval  # Intervalo en segundos, por ejemplo, 86400 para 1 día
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        logging.info("Suscripción exitosa!")
        logging.info(response.json())
    else:
        logging.error(f"Error en la suscripción: {response.status_code} {response.text}")

# Función para obtener datos de mercado
def fetch_data(symbol, timeframe):
    path = "/md/kline"
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

# Función para registrar operaciones
def log_trade(action, price, quantity):
    logging.info(f"{action.capitalize()} | Precio: {price} | Cantidad: {quantity}")

# Función de operaciones básicas
def place_market_order(symbol, side, quantity):
    path = "/spot/orders"
    data = {
        "symbol": symbol,
        "side": side.upper(),
        "qtyType": "ByBase",  # Usar la cantidad base (en este caso, BTC)
        "quoteQtyEv": 0,  # Esto se usa solo si envías por cantidad de cotización
        "baseQtyEv": int(quantity * 1e8),  # Convertir la cantidad a unidades pequeñas de la moneda base (BTC)
        "priceEp": 0,  # Para órdenes de mercado, el precio es 0
        "ordType": "Market",  # Orden de tipo Market
        "timeInForce": "GoodTillCancel",  # La orden es válida hasta que se ejecute o la canceles
        "text": ""  # Comentario opcional para la orden
    }
    return make_request("POST", path, data=data)

# Función principal del bot
def run_bot():
    trades = []
    position = None

    logging.info("Iniciando bot y suscribiendo a Kline...")
    subscribe_to_kline(SYMBOL, TIMEFRAME)

    while True:
        try:
            logging.info("Iniciando nuevo ciclo del bot.")
            data = fetch_data(SYMBOL, TIMEFRAME)
            if data.empty:
                logging.warning("No se pudieron obtener datos de velas.")
                time.sleep(60)
                continue

            latest = data.iloc[-1]
            balance = 0.1  # Simulando un balance de ejemplo

            quantity = balance / latest['close']

            # Lógica de compra/venta
            if latest['close'] < 20000 and position is None:
                logging.info("Señal de compra detectada.")
                order = place_market_order(SYMBOL, "buy", quantity)
                if order:
                    position = {"side": "buy", "entry_price": latest['close']}
                    log_trade("compra", latest['close'], quantity)

            elif latest['close'] > 25000 and position:
                logging.info("Señal de venta detectada.")
                order = place_market_order(SYMBOL, "sell", quantity)
                if order:
                    position = None
                    log_trade("venta", latest['close'], quantity)

        except Exception as e:
            logging.error(f"Error en el ciclo del bot: {e}")

        time.sleep(60)

if __name__ == "__main__":
    run_bot()
